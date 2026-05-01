"""
Train LightGBM p50 demand model and export artifacts.
"""
import argparse
import json
import pickle
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor


DAYPARTS = ["morning", "midday", "evening"]

SKU_MASTER = {
    "traditional_baguette": {"sku_name": "Traditional Baguette", "sku_category": "Bread"},
    "butter_croissant": {"sku_name": "Butter Croissant", "sku_category": "Pastry"},
    "pain_au_chocolat": {"sku_name": "Pain au Chocolat", "sku_category": "Pastry"},
    "country_sourdough": {"sku_name": "Country Sourdough", "sku_category": "Bread"},
    "blueberry_muffin": {"sku_name": "Blueberry Muffin", "sku_category": "Dessert"},
    "chocolate_cookie": {"sku_name": "Chocolate Cookie", "sku_category": "Dessert"},
    "brownie": {"sku_name": "Brownie", "sku_category": "Dessert"},
    "fruit_tart": {"sku_name": "Fruit Tart", "sku_category": "Dessert"},
    "cake_slice": {"sku_name": "Cake Slice", "sku_category": "Dessert"},
    "ham_cheese_sandwich": {"sku_name": "Ham & Cheese Sandwich", "sku_category": "Savory"},
    "brioche": {"sku_name": "Brioche", "sku_category": "Pastry"},
    "coffee_bun_sweet_bun": {"sku_name": "Coffee Bun / Sweet Bun", "sku_category": "Pastry"},
}

OUTLET_PROFILES = {
    "cheras_hub": {"outlet_factor": 1.10},
    "setapak_town": {"outlet_factor": 1.00},
    "shah_alam_sek7": {"outlet_factor": 0.95},
    "kajang_town": {"outlet_factor": 0.90},
    "klang_riverside": {"outlet_factor": 0.92},
}

DAYPART_FACTORS = {"morning": 1.10, "midday": 1.00, "evening": 0.90}


@dataclass
class Paths:
    input_csv: Path
    models_dir: Path
    exports_dir: Path

    @property
    def model_path(self) -> Path:
        return self.models_dir / "lightgbm_p50_v1.pkl"

    @property
    def model_compat_path(self) -> Path:
        return self.models_dir / "model.pkl"

    @property
    def residual_bands_path(self) -> Path:
        return self.models_dir / "residual_bands_v1.json"

    @property
    def metrics_path(self) -> Path:
        return self.models_dir / "model_metrics_v1.json"

    @property
    def metadata_path(self) -> Path:
        return self.models_dir / "metadata.json"

    @property
    def feature_schema_path(self) -> Path:
        return self.models_dir / "feature_schema.json"

    @property
    def feature_schema_v1_path(self) -> Path:
        return self.models_dir / "feature_schema_v1.json"

    @property
    def feature_table_path(self) -> Path:
        return self.exports_dir / "feature_table.csv"

    @property
    def validation_predictions_path(self) -> Path:
        return self.exports_dir / "validation_predictions.csv"


def parse_unit_price(value: Optional[str]) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    text = text.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_article(text: str) -> str:
    return " ".join(str(text).upper().split())


def assign_daypart(hour: int) -> str:
    if 6 <= hour < 11:
        return "morning"
    if 11 <= hour < 16:
        return "midday"
    return "evening"


def map_article_to_sku(article: str) -> Optional[str]:
    article_upper = normalize_article(article)
    # Order matters: more specific matches first.
    patterns = [
        (r"PAIN AU CHOCOLAT", "pain_au_chocolat"),
        (r"CROISSANT", "butter_croissant"),
        (r"TRADITIONAL BAGUETTE", "traditional_baguette"),
        (r"BAGUETTE", "traditional_baguette"),
        (r"BRIOCHE", "brioche"),
        (r"SAND|SANDWICH", "ham_cheese_sandwich"),
        (r"MUFFIN", "blueberry_muffin"),
        (r"COOKIE|BISCUIT", "chocolate_cookie"),
        (r"BROWNIE", "brownie"),
        (r"TARTE|TART", "fruit_tart"),
        (r"CAKE|GATEAU", "cake_slice"),
        (r"KOUIGN|BUN|CHOUQUETTE|PAIN AU LAIT", "coffee_bun_sweet_bun"),
        (r"PAIN|BOULE|SPECIAL BREAD", "country_sourdough"),
    ]
    for pattern, sku_id in patterns:
        if re.search(pattern, article_upper):
            return sku_id
    return None


def load_transactions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

    if "quantity" not in df.columns:
        raise ValueError("CSV must include a quantity column")
    if "article" not in df.columns:
        raise ValueError("CSV must include an article column")
    if "date" not in df.columns or "time" not in df.columns:
        raise ValueError("CSV must include date and time columns")

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df = df[df["quantity"] > 0].copy()
    df["article"] = df["article"].astype(str).apply(normalize_article)

    if "unit_price" not in df.columns:
        df["unit_price"] = None
    df["unit_price"] = df["unit_price"].apply(parse_unit_price)

    timestamp = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce")
    df = df[timestamp.notna()].copy()
    df["timestamp"] = timestamp[timestamp.notna()]
    df["date"] = df["timestamp"].dt.normalize()
    df["hour"] = df["timestamp"].dt.hour
    df["daypart"] = df["hour"].apply(assign_daypart)
    return df


def build_base_demand(df: pd.DataFrame) -> pd.DataFrame:
    df["sku_id"] = df["article"].apply(map_article_to_sku)
    df = df[df["sku_id"].notna()].copy()

    df["sku_name"] = df["sku_id"].apply(lambda x: SKU_MASTER[x]["sku_name"])
    df["sku_category"] = df["sku_id"].apply(lambda x: SKU_MASTER[x]["sku_category"])

    grouped = (
        df.groupby(["date", "sku_id", "sku_name", "sku_category", "daypart"], as_index=False)
        .agg(base_quantity_sold=("quantity", "sum"), avg_unit_price=("unit_price", "mean"))
    )
    grouped["base_quantity_sold"] = grouped["base_quantity_sold"].clip(lower=0).round().astype(int)
    return grouped


def ensure_time_series(base_df: pd.DataFrame, days: int) -> pd.DataFrame:
    max_date = base_df["date"].max()
    min_date = max_date - pd.Timedelta(days=days - 1)
    base_df = base_df[(base_df["date"] >= min_date) & (base_df["date"] <= max_date)].copy()

    sku_ids = list(SKU_MASTER.keys())
    dates = pd.date_range(min_date, max_date, freq="D")

    grid = pd.MultiIndex.from_product([dates, sku_ids, DAYPARTS], names=["date", "sku_id", "daypart"]).to_frame(index=False)
    grid["sku_name"] = grid["sku_id"].apply(lambda x: SKU_MASTER[x]["sku_name"])
    grid["sku_category"] = grid["sku_id"].apply(lambda x: SKU_MASTER[x]["sku_category"])

    merged = grid.merge(base_df, on=["date", "sku_id", "sku_name", "sku_category", "daypart"], how="left")
    merged["base_quantity_sold"] = merged["base_quantity_sold"].fillna(0).round().astype(int)
    if merged["avg_unit_price"].notna().any():
        merged["avg_unit_price"] = merged["avg_unit_price"].fillna(merged["avg_unit_price"].median())
    else:
        merged["avg_unit_price"] = 0.0
    return merged


def expand_to_outlets(base_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    outlets = []
    for outlet_id, profile in OUTLET_PROFILES.items():
        outlet_factor = profile["outlet_factor"]
        outlet_df = base_df.copy()
        outlet_df["outlet_id"] = outlet_id
        outlet_df["outlet_factor"] = outlet_factor
        outlets.append(outlet_df)

    expanded = pd.concat(outlets, ignore_index=True)
    expanded["daypart_factor"] = expanded["daypart"].map(DAYPART_FACTORS)
    noise = rng.normal(loc=1.0, scale=0.08, size=len(expanded))

    expanded["estimated_true_demand"] = (
        expanded["base_quantity_sold"] * expanded["outlet_factor"] * expanded["daypart_factor"] * noise
    )
    expanded["estimated_true_demand"] = expanded["estimated_true_demand"].clip(lower=0).round().astype(int)
    expanded["actual_sales"] = expanded["estimated_true_demand"]
    return expanded


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_year"] = df["date"].dt.dayofyear
    return df


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["outlet_id", "sku_id", "daypart", "date"]).copy()
    group_cols = ["outlet_id", "sku_id", "daypart"]
    df["lag_7"] = df.groupby(group_cols)["estimated_true_demand"].shift(7)
    df["lag_30"] = df.groupby(group_cols)["estimated_true_demand"].shift(30)
    df["rolling_mean_7"] = df.groupby(group_cols)["estimated_true_demand"].transform(
        lambda s: s.shift(1).rolling(7).mean()
    )
    df["rolling_mean_30"] = df.groupby(group_cols)["estimated_true_demand"].transform(
        lambda s: s.shift(1).rolling(30).mean()
    )
    return df


def compute_wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(actual - predicted)) / denom)


def compute_bias(actual: np.ndarray, predicted: np.ndarray) -> float:
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return 0.0
    return float(np.sum(predicted - actual) / denom)


def calculate_residual_bands(df: pd.DataFrame, min_count: int = 30) -> Dict[str, Dict[str, float]]:
    df = df.copy()
    df["group_key"] = df["sku_category"].astype(str) + "|" + df["daypart"].astype(str)

    global_p10 = float(np.percentile(df["residual"], 10))
    global_p90 = float(np.percentile(df["residual"], 90))

    bands = {}
    for group_key, group in df.groupby("group_key"):
        if len(group) < min_count:
            continue
        bands[group_key] = {
            "p10": float(np.percentile(group["residual"], 10)),
            "p90": float(np.percentile(group["residual"], 90)),
            "count": int(len(group)),
        }

    return {
        "global": {"p10": global_p10, "p90": global_p90, "count": int(len(df))},
        "by_group": bands,
    }


def apply_residual_bands(df: pd.DataFrame, bands: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    df = df.copy()
    df["group_key"] = df["sku_category"].astype(str) + "|" + df["daypart"].astype(str)

    def lookup_band(key: str, band_name: str) -> float:
        if key in bands.get("by_group", {}):
            return float(bands["by_group"][key][band_name])
        return float(bands["global"][band_name])

    df["residual_p10"] = df["group_key"].apply(lambda x: lookup_band(x, "p10"))
    df["residual_p90"] = df["group_key"].apply(lambda x: lookup_band(x, "p90"))
    df["predicted_p10"] = (df["predicted_p50"] + df["residual_p10"]).clip(lower=0)
    df["predicted_p90"] = (df["predicted_p50"] + df["residual_p90"]).clip(lower=0)
    return df


def build_feature_schema(feature_columns: List[str], categorical_columns: List[str]) -> Dict[str, object]:
    return {
        "version": "v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "estimated_true_demand",
        "feature_columns": feature_columns,
        "categorical_columns": categorical_columns,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LightGBM p50 model and export artifacts.")
    parser.add_argument("--input", default="Bakery sales.csv", help="Path to French Bakery CSV")
    parser.add_argument("--days", type=int, default=180, help="Number of days to keep for training")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--models-dir", default="models", help="Output models directory")
    parser.add_argument("--exports-dir", default="exports", help="Output exports directory")
    args = parser.parse_args()

    paths = Paths(
        input_csv=Path(args.input),
        models_dir=Path(args.models_dir),
        exports_dir=Path(args.exports_dir),
    )

    paths.models_dir.mkdir(parents=True, exist_ok=True)
    paths.exports_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)

    raw_df = load_transactions(paths.input_csv)
    base_df = build_base_demand(raw_df)
    base_df = ensure_time_series(base_df, args.days)
    expanded_df = expand_to_outlets(base_df, rng)
    expanded_df = add_calendar_features(expanded_df)
    expanded_df = add_lag_features(expanded_df)

    feature_columns = [
        "outlet_id",
        "sku_id",
        "sku_category",
        "daypart",
        "day_of_week",
        "is_weekend",
        "month",
        "week_of_year",
        "day_of_year",
        "lag_7",
        "lag_30",
        "rolling_mean_7",
        "rolling_mean_30",
    ]
    categorical_columns = ["outlet_id", "sku_id", "sku_category", "daypart"]

    feature_df = expanded_df.dropna(subset=["lag_7", "lag_30", "rolling_mean_7", "rolling_mean_30"]).copy()

    for col in categorical_columns:
        feature_df[col] = feature_df[col].astype("category")

    all_dates = sorted(expanded_df["date"].unique())
    if len(all_dates) <= 30:
        raise ValueError("Not enough days to build a 30-day validation window")

    train_cut = min(150, len(all_dates) - 30)
    train_dates = all_dates[:train_cut]
    val_dates = all_dates[train_cut:train_cut + 30]

    train_df = feature_df[feature_df["date"].isin(train_dates)]
    val_df = feature_df[feature_df["date"].isin(val_dates)]

    X_train = train_df[feature_columns]
    y_train = train_df["estimated_true_demand"].to_numpy()
    X_val = val_df[feature_columns]
    y_val = val_df["estimated_true_demand"].to_numpy()

    model = LGBMRegressor(
        objective="quantile",
        alpha=0.5,
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=64,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=args.seed,
    )
    model.fit(X_train, y_train, categorical_feature=categorical_columns)

    val_pred = model.predict(X_val)
    val_pred = np.clip(val_pred, 0, None)

    wape = compute_wape(y_val, val_pred)
    bias = compute_bias(y_val, val_pred)

    val_results = val_df.copy()
    val_results["predicted_p50"] = val_pred
    val_results["residual"] = val_results["estimated_true_demand"] - val_results["predicted_p50"]

    residual_bands = calculate_residual_bands(val_results)
    val_results = apply_residual_bands(val_results, residual_bands)

    coverage = float(
        np.mean(
            (val_results["estimated_true_demand"] >= val_results["predicted_p10"])
            & (val_results["estimated_true_demand"] <= val_results["predicted_p90"])
        )
    )

    metrics = {
        "model_version": "v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "training_rows": int(len(train_df)),
        "validation_rows": int(len(val_df)),
        "train_days": int(len(train_dates)),
        "validation_days": int(len(val_dates)),
        "validation_window": "last 30 days",
        "wape": wape,
        "bias": bias,
        "p10_p90_coverage": coverage,
        "target": "estimated_true_demand",
        "feature_columns": feature_columns,
        "categorical_columns": categorical_columns,
    }

    feature_schema = build_feature_schema(feature_columns, categorical_columns)

    with open(paths.model_path, "wb") as f:
        pickle.dump(model, f)

    with open(paths.model_compat_path, "wb") as f:
        pickle.dump(model, f)

    with open(paths.residual_bands_path, "w", encoding="utf-8") as f:
        json.dump(residual_bands, f, indent=2)

    with open(paths.metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    metadata = {
        "model_version": metrics["model_version"],
        "created_at": metrics["created_at"],
        "wape": metrics["wape"],
        "bias": metrics["bias"],
        "p10_p90_coverage": metrics["p10_p90_coverage"],
        "residual_bands": residual_bands,
    }

    with open(paths.metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with open(paths.feature_schema_path, "w", encoding="utf-8") as f:
        json.dump(feature_schema, f, indent=2)

    with open(paths.feature_schema_v1_path, "w", encoding="utf-8") as f:
        json.dump(feature_schema, f, indent=2)

    feature_df.to_csv(paths.feature_table_path, index=False)

    export_cols = [
        "date",
        "outlet_id",
        "sku_id",
        "sku_category",
        "daypart",
        "estimated_true_demand",
        "predicted_p50",
        "predicted_p10",
        "predicted_p90",
        "residual",
    ]
    val_results[export_cols].to_csv(paths.validation_predictions_path, index=False)

    print("Artifacts written:")
    print(f"- {paths.model_path}")
    print(f"- {paths.model_compat_path}")
    print(f"- {paths.residual_bands_path}")
    print(f"- {paths.metrics_path}")
    print(f"- {paths.metadata_path}")
    print(f"- {paths.feature_schema_path}")
    print(f"- {paths.feature_table_path}")
    print(f"- {paths.validation_predictions_path}")


if __name__ == "__main__":
    main()
