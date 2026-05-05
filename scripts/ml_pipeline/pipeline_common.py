"""
Shared utilities for the Predictory ML pipeline.

The numbered scripts in this folder are intentionally thin entrypoints. This
module keeps the implementation in one place while still making each pipeline
stage runnable and inspectable.
"""
from __future__ import annotations

import argparse
import json
import pickle
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor


DAYPARTS = ["morning", "midday", "evening"]

SKU_MASTER = {
    "traditional_baguette": {"sku_name": "Traditional Baguette", "sku_category": "Bread", "unit_price": 3.20},
    "butter_croissant": {"sku_name": "Butter Croissant", "sku_category": "Pastry", "unit_price": 4.25},
    "pain_au_chocolat": {"sku_name": "Pain au Chocolat", "sku_category": "Pastry", "unit_price": 4.40},
    "country_sourdough": {"sku_name": "Country Sourdough", "sku_category": "Bread", "unit_price": 6.00},
    "blueberry_muffin": {"sku_name": "Blueberry Muffin", "sku_category": "Dessert", "unit_price": 3.80},
    "chocolate_cookie": {"sku_name": "Chocolate Cookie", "sku_category": "Dessert", "unit_price": 2.50},
    "brownie": {"sku_name": "Brownie", "sku_category": "Dessert", "unit_price": 4.00},
    "fruit_tart": {"sku_name": "Fruit Tart", "sku_category": "Dessert", "unit_price": 5.50},
    "cake_slice": {"sku_name": "Cake Slice", "sku_category": "Dessert", "unit_price": 6.20},
    "ham_cheese_sandwich": {"sku_name": "Ham & Cheese Sandwich", "sku_category": "Savory", "unit_price": 8.50},
    "brioche": {"sku_name": "Brioche", "sku_category": "Pastry", "unit_price": 3.80},
    "coffee_bun_sweet_bun": {"sku_name": "Coffee Bun / Sweet Bun", "sku_category": "Pastry", "unit_price": 3.20},
}

OUTLET_PROFILES = {
    "klcc_mall": {"outlet_name": "KLCC Mall", "outlet_type": "mall", "outlet_factor": 1.18},
    "mid_valley_mall": {"outlet_name": "Mid Valley Mall", "outlet_type": "mall", "outlet_factor": 1.12},
    "mont_kiara_premium": {"outlet_name": "Mont Kiara Premium", "outlet_type": "premium", "outlet_factor": 1.08},
    "bangsar_street": {"outlet_name": "Bangsar Street", "outlet_type": "street_cafe", "outlet_factor": 0.92},
    "subang_residential": {
        "outlet_name": "Subang Residential",
        "outlet_type": "residential_neighbourhood",
        "outlet_factor": 0.82,
    },
}

DAYPART_FACTORS = {"morning": 1.10, "midday": 1.00, "evening": 0.90}
FEATURE_COLUMNS = [
    "outlet_id",
    "sku_id",
    "sku_category",
    "daypart",
    "day_of_week",
    "is_weekend",
    "month",
    "week_of_year",
    "day_of_year",
    "weather_condition",
    "rain_mm",
    "temperature",
    "is_holiday",
    "promo_flag",
    "event_flag",
    "recent_waste_pressure",
    "recent_stockout_pressure",
    "lag_7",
    "lag_30",
    "rolling_mean_7",
    "rolling_mean_30",
]
CAT_COLUMNS = ["outlet_id", "sku_id", "sku_category", "daypart", "weather_condition"]


@dataclass
class PipelinePaths:
    repo_root: Path
    input_csv: Path
    pipeline_dir: Path
    models_dir: Path
    backend_models_dir: Path
    exports_dir: Path

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "PipelinePaths":
        repo_root = Path(args.repo_root).resolve()
        return cls(
            repo_root=repo_root,
            input_csv=(repo_root / args.input).resolve(),
            pipeline_dir=(repo_root / args.pipeline_dir).resolve(),
            models_dir=(repo_root / args.models_dir).resolve(),
            backend_models_dir=(repo_root / args.backend_models_dir).resolve(),
            exports_dir=(repo_root / args.exports_dir).resolve(),
        )

    def ensure_dirs(self) -> None:
        for directory in [
            self.pipeline_dir,
            self.models_dir,
            self.backend_models_dir,
            self.exports_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


def add_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--input", default="Bakery sales.csv", help="Bakery sales CSV")
    parser.add_argument("--pipeline-dir", default="exports/ml_pipeline", help="Intermediate pipeline directory")
    parser.add_argument("--models-dir", default="backend/models", help="Primary model artifact directory")
    parser.add_argument("--backend-models-dir", default="backend/models", help="Backend model drop-in directory")
    parser.add_argument("--exports-dir", default="exports/ml_pipeline", help="Export artifact directory")
    parser.add_argument("--days", type=int, default=180, help="Days of source history to keep")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def parse_unit_price(value: Optional[str]) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip().replace("â‚¬", "").replace("€", "").replace(" ", "").replace(",", ".")
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


def step_01_ingest(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.input_csv)
    df.columns = [col.strip().lower() for col in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    required = {"date", "time", "article", "quantity"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

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
    output = paths.pipeline_dir / "01_transactions.csv"
    df.to_csv(output, index=False)
    return output


def step_02_map_skus(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "01_transactions.csv", parse_dates=["date", "timestamp"])
    df["sku_id"] = df["article"].apply(map_article_to_sku)
    df = df[df["sku_id"].notna()].copy()
    df["sku_name"] = df["sku_id"].map(lambda value: SKU_MASTER[value]["sku_name"])
    df["sku_category"] = df["sku_id"].map(lambda value: SKU_MASTER[value]["sku_category"])
    grouped = (
        df.groupby(["date", "sku_id", "sku_name", "sku_category", "daypart"], as_index=False)
        .agg(base_quantity_sold=("quantity", "sum"), avg_unit_price=("unit_price", "mean"))
    )
    grouped["base_quantity_sold"] = grouped["base_quantity_sold"].clip(lower=0).round().astype(int)
    grouped["avg_unit_price"] = grouped.apply(
        lambda row: row["avg_unit_price"]
        if pd.notna(row["avg_unit_price"])
        else SKU_MASTER[row["sku_id"]]["unit_price"],
        axis=1,
    )
    output = paths.pipeline_dir / "02_sku_demand.csv"
    grouped.to_csv(output, index=False)
    return output


def step_03_generate_outlets(paths: PipelinePaths, days: int, seed: int) -> Path:
    rng = np.random.default_rng(seed)
    base_df = pd.read_csv(paths.pipeline_dir / "02_sku_demand.csv", parse_dates=["date"])
    max_date = base_df["date"].max()
    min_date = max_date - pd.Timedelta(days=days - 1)
    base_df = base_df[(base_df["date"] >= min_date) & (base_df["date"] <= max_date)].copy()
    grid = pd.MultiIndex.from_product(
        [pd.date_range(min_date, max_date, freq="D"), list(SKU_MASTER.keys()), DAYPARTS],
        names=["date", "sku_id", "daypart"],
    ).to_frame(index=False)
    grid["sku_name"] = grid["sku_id"].map(lambda value: SKU_MASTER[value]["sku_name"])
    grid["sku_category"] = grid["sku_id"].map(lambda value: SKU_MASTER[value]["sku_category"])
    merged = grid.merge(base_df, on=["date", "sku_id", "sku_name", "sku_category", "daypart"], how="left")
    merged["base_quantity_sold"] = merged["base_quantity_sold"].fillna(0).round().astype(int)
    merged["avg_unit_price"] = merged.apply(
        lambda row: row["avg_unit_price"]
        if pd.notna(row["avg_unit_price"])
        else SKU_MASTER[row["sku_id"]]["unit_price"],
        axis=1,
    )

    frames = []
    for outlet_id, profile in OUTLET_PROFILES.items():
        outlet_df = merged.copy()
        outlet_df["outlet_id"] = outlet_id
        outlet_df["outlet_name"] = profile["outlet_name"]
        outlet_df["outlet_type"] = profile["outlet_type"]
        outlet_df["outlet_factor"] = profile["outlet_factor"]
        frames.append(outlet_df)

    expanded = pd.concat(frames, ignore_index=True)
    expanded["daypart_factor"] = expanded["daypart"].map(DAYPART_FACTORS)
    expanded["demand_noise"] = rng.normal(loc=1.0, scale=0.08, size=len(expanded))
    output = paths.pipeline_dir / "03_outlet_demand.csv"
    expanded.to_csv(output, index=False)
    return output


def step_04_simulate_context(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "03_outlet_demand.csv", parse_dates=["date"])
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_year"] = df["date"].dt.dayofyear
    df["weather_condition"] = np.where(df["day_of_week"].isin([5, 6]), "clear", "light_rain")
    df["rain_mm"] = np.where(df["weather_condition"] == "light_rain", 3.4, 0.0)
    df["temperature"] = np.where(df["weather_condition"] == "light_rain", 28.2, 29.5)
    df["is_holiday"] = ((df["month"] == 12) & (df["date"].dt.day >= 24)).astype(int)
    df["holiday_name"] = np.where(df["is_holiday"] == 1, "year_end_peak", "")
    df["promo_flag"] = ((df["day_of_week"] == 4) & df["sku_category"].isin(["Pastry", "Dessert"])).astype(int)
    df["promo_type"] = np.where(df["promo_flag"] == 1, "weekend_bundle", "")
    df["event_flag"] = ((df["outlet_id"].str.contains("mall")) & (df["is_weekend"] == 1)).astype(int)
    df["event_description"] = np.where(df["event_flag"] == 1, "mall_weekend_traffic", "")
    output = paths.pipeline_dir / "04_context.csv"
    df.to_csv(output, index=False)
    return output


def step_05_simulate_ops(paths: PipelinePaths, seed: int) -> Path:
    rng = np.random.default_rng(seed + 5)
    df = pd.read_csv(paths.pipeline_dir / "04_context.csv", parse_dates=["date"])
    df["estimated_true_demand"] = (
        df["base_quantity_sold"] * df["outlet_factor"] * df["daypart_factor"] * df["demand_noise"]
    ).clip(lower=0).round().astype(int)
    prep_bias = rng.normal(loc=0.96, scale=0.10, size=len(df))
    df["planned_prep"] = (df["estimated_true_demand"] * prep_bias).clip(lower=0).round().astype(int)
    df["actual_sales"] = np.minimum(df["estimated_true_demand"], df["planned_prep"])
    df["waste_units"] = (df["planned_prep"] - df["actual_sales"]).clip(lower=0)
    df["stockout_units"] = (df["estimated_true_demand"] - df["actual_sales"]).clip(lower=0)
    df["recent_waste_pressure"] = (df["waste_units"] > df["waste_units"].quantile(0.75)).astype(int)
    df["recent_stockout_pressure"] = (df["stockout_units"] > df["stockout_units"].quantile(0.75)).astype(int)
    output = paths.pipeline_dir / "05_ops.csv"
    df.to_csv(output, index=False)
    return output


def step_06_recover_demand(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "05_ops.csv", parse_dates=["date"])
    df["recovered_demand"] = df["actual_sales"] + df["stockout_units"]
    df["estimated_true_demand"] = df["recovered_demand"].clip(lower=0).round().astype(int)
    output = paths.pipeline_dir / "06_recovered_demand.csv"
    df.to_csv(output, index=False)
    return output


def step_07_build_features(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "06_recovered_demand.csv", parse_dates=["date"])
    df = df.sort_values(["outlet_id", "sku_id", "daypart", "date"]).copy()
    group_cols = ["outlet_id", "sku_id", "daypart"]
    df["lag_7"] = df.groupby(group_cols)["estimated_true_demand"].shift(7)
    df["lag_30"] = df.groupby(group_cols)["estimated_true_demand"].shift(30)
    df["rolling_mean_7"] = df.groupby(group_cols)["estimated_true_demand"].transform(
        lambda series: series.shift(1).rolling(7).mean()
    )
    df["rolling_mean_30"] = df.groupby(group_cols)["estimated_true_demand"].transform(
        lambda series: series.shift(1).rolling(30).mean()
    )
    df = df.dropna(subset=["lag_7", "lag_30", "rolling_mean_7", "rolling_mean_30"]).copy()
    pipeline_output = paths.pipeline_dir / "07_features.csv"
    df.to_csv(pipeline_output, index=False)
    df.to_csv(paths.exports_dir / "feature_table.csv", index=False)
    write_json(
        paths.pipeline_dir / "feature_table_summary_step7.json",
        {"rows": int(len(df)), "min_date": str(df["date"].min().date()), "max_date": str(df["date"].max().date())},
    )
    return pipeline_output


def compute_wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    denom = np.sum(np.abs(actual))
    return 0.0 if denom == 0 else float(np.sum(np.abs(actual - predicted)) / denom)


def compute_bias(actual: np.ndarray, predicted: np.ndarray) -> float:
    denom = np.sum(np.abs(actual))
    return 0.0 if denom == 0 else float(np.sum(predicted - actual) / denom)


def build_feature_schema(encoded_columns: Optional[List[str]] = None) -> Dict[str, object]:
    return {
        "version": "v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "estimated_true_demand",
        "feature_columns": FEATURE_COLUMNS,
        "categorical_columns": CAT_COLUMNS,
        "encoded_feature_columns": encoded_columns or [],
    }


def step_08_train_model(paths: PipelinePaths, seed: int) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "07_features.csv", parse_dates=["date"])
    for column in CAT_COLUMNS:
        df[column] = df[column].astype("category")
    all_dates = sorted(df["date"].unique())
    if len(all_dates) <= 30:
        raise ValueError("Not enough days to build a 30-day validation window")
    train_dates = all_dates[: max(1, len(all_dates) - 30)]
    val_dates = all_dates[len(train_dates) :]
    train_df = df[df["date"].isin(train_dates)].copy()
    val_df = df[df["date"].isin(val_dates)].copy()

    model = LGBMRegressor(
        objective="quantile",
        alpha=0.5,
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=64,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=seed,
    )
    model.fit(train_df[FEATURE_COLUMNS], train_df["estimated_true_demand"], categorical_feature=CAT_COLUMNS)
    val_pred = np.clip(model.predict(val_df[FEATURE_COLUMNS]), 0, None)
    val_results = val_df.copy()
    val_results["predicted_p50"] = val_pred
    val_results["residual"] = val_results["estimated_true_demand"] - val_results["predicted_p50"]
    val_results.to_csv(paths.pipeline_dir / "08_validation_predictions_raw.csv", index=False)

    metrics = {
        "model_version": "lightgbm_p50_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "training_rows": int(len(train_df)),
        "validation_rows": int(len(val_df)),
        "train_days": int(len(train_dates)),
        "validation_days": int(len(val_dates)),
        "validation_window": "last_30_days",
        "wape": compute_wape(val_results["estimated_true_demand"].to_numpy(), val_pred),
        "bias": compute_bias(val_results["estimated_true_demand"].to_numpy(), val_pred),
        "target": "estimated_true_demand",
        "feature_columns": FEATURE_COLUMNS,
        "categorical_columns": CAT_COLUMNS,
    }

    for directory in [paths.models_dir, paths.backend_models_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "lightgbm_p50_v1.pkl").open("wb") as handle:
            pickle.dump(model, handle)
        with (directory / "model.pkl").open("wb") as handle:
            pickle.dump(model, handle)
        write_json(directory / "model_metrics_v1.json", metrics)
        write_json(directory / "feature_schema_v1.json", build_feature_schema())
    return paths.models_dir / "lightgbm_p50_v1.pkl"


def calculate_residual_bands(df: pd.DataFrame, min_count: int = 30) -> Dict[str, object]:
    df = df.copy()
    df["group_key"] = df["sku_category"].astype(str) + "|" + df["daypart"].astype(str)
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
        "global": {
            "p10": float(np.percentile(df["residual"], 10)),
            "p90": float(np.percentile(df["residual"], 90)),
            "count": int(len(df)),
        },
        "by_group": bands,
    }


def apply_residual_bands(df: pd.DataFrame, bands: Dict[str, object]) -> pd.DataFrame:
    df = df.copy()
    by_group = bands.get("by_group", {})
    global_band = bands["global"]
    df["group_key"] = df["sku_category"].astype(str) + "|" + df["daypart"].astype(str)

    def band_value(group_key: str, name: str) -> float:
        if isinstance(by_group, dict) and group_key in by_group:
            return float(by_group[group_key][name])
        return float(global_band[name])

    df["predicted_p10"] = (df["predicted_p50"] + df["group_key"].map(lambda key: band_value(key, "p10"))).clip(lower=0)
    df["predicted_p90"] = (df["predicted_p50"] + df["group_key"].map(lambda key: band_value(key, "p90"))).clip(lower=0)
    return df


def step_09_build_bands(paths: PipelinePaths) -> Path:
    val = pd.read_csv(paths.pipeline_dir / "08_validation_predictions_raw.csv", parse_dates=["date"])
    bands = calculate_residual_bands(val)
    val = apply_residual_bands(val, bands)
    val.to_csv(paths.exports_dir / "validation_predictions.csv", index=False)
    coverage = float(
        np.mean(
            (val["estimated_true_demand"] >= val["predicted_p10"])
            & (val["estimated_true_demand"] <= val["predicted_p90"])
        )
    )
    bands["coverage"] = coverage
    for directory in [paths.models_dir, paths.backend_models_dir]:
        write_json(directory / "residual_bands_v1.json", bands)
    return paths.models_dir / "residual_bands_v1.json"


def load_model(paths: PipelinePaths):
    with (paths.models_dir / "lightgbm_p50_v1.pkl").open("rb") as handle:
        return pickle.load(handle)


def step_10_generate_forecast(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "07_features.csv", parse_dates=["date"])
    latest_date = df["date"].max()
    forecast_date = latest_date + pd.Timedelta(days=1)
    latest = df[df["date"] == latest_date].copy()
    latest["date"] = forecast_date
    latest["day_of_week"] = forecast_date.dayofweek
    latest["is_weekend"] = int(forecast_date.dayofweek >= 5)
    latest["month"] = forecast_date.month
    latest["week_of_year"] = int(forecast_date.isocalendar().week)
    latest["day_of_year"] = forecast_date.dayofyear
    for column in CAT_COLUMNS:
        latest[column] = latest[column].astype("category")
    model = load_model(paths)
    latest["predicted_p50"] = np.clip(model.predict(latest[FEATURE_COLUMNS]), 0, None)
    with (paths.models_dir / "residual_bands_v1.json").open("r", encoding="utf-8") as handle:
        bands = json.load(handle)
    latest = apply_residual_bands(latest, bands)
    output = paths.pipeline_dir / "10_forecast_lines.csv"
    latest.to_csv(output, index=False)
    return output


def rounded_batch(value: float, batch_size: int = 5) -> int:
    if value <= 0:
        return 0
    return int(round(value / batch_size) * batch_size)


def step_11_optimize_prep(paths: PipelinePaths) -> Path:
    df = pd.read_csv(paths.pipeline_dir / "10_forecast_lines.csv", parse_dates=["date"])
    waste_cost_per_unit = df["avg_unit_price"].fillna(0) * 0.45
    stockout_cost_per_unit = df["avg_unit_price"].fillna(0) * 1.25
    posture = np.where(stockout_cost_per_unit > waste_cost_per_unit * 1.5, "above_p50_service_protection", "near_p50_balanced")
    df["recommended_prep_qty"] = [
        rounded_batch(p90 if pos == "above_p50_service_protection" else p50)
        for p50, p90, pos in zip(df["predicted_p50"], df["predicted_p90"], posture)
    ]
    df["decision_posture"] = posture
    df["expected_waste_units"] = (df["recommended_prep_qty"] - df["predicted_p50"]).clip(lower=0)
    df["expected_stockout_units"] = (df["predicted_p50"] - df["recommended_prep_qty"]).clip(lower=0)
    df["expected_cost"] = df["expected_waste_units"] * waste_cost_per_unit + df["expected_stockout_units"] * stockout_cost_per_unit
    df["explanation"] = df.apply(
        lambda row: (
            f"For {row['sku_name']} at {row['outlet_name']} during {row['daypart']}, forecast demand range is "
            f"{row['predicted_p10']:.0f}-{row['predicted_p90']:.0f} units with median {row['predicted_p50']:.0f}. "
            f"Recommended prep is {row['recommended_prep_qty']} units."
        ),
        axis=1,
    )
    output = paths.pipeline_dir / "11_optimized_recommendations.csv"
    df.to_csv(output, index=False)
    return output


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


STEP_FUNCS = {
    "01": lambda paths, args: step_01_ingest(paths),
    "02": lambda paths, args: step_02_map_skus(paths),
    "03": lambda paths, args: step_03_generate_outlets(paths, args.days, args.seed),
    "04": lambda paths, args: step_04_simulate_context(paths),
    "05": lambda paths, args: step_05_simulate_ops(paths, args.seed),
    "06": lambda paths, args: step_06_recover_demand(paths),
    "07": lambda paths, args: step_07_build_features(paths),
    "08": lambda paths, args: step_08_train_model(paths, args.seed),
    "09": lambda paths, args: step_09_build_bands(paths),
    "10": lambda paths, args: step_10_generate_forecast(paths),
    "11": lambda paths, args: step_11_optimize_prep(paths),
}


def run_steps(step_ids: Iterable[str], args: argparse.Namespace) -> List[Path]:
    paths = PipelinePaths.from_args(args)
    paths.ensure_dirs()
    outputs = []
    for step_id in step_ids:
        output = STEP_FUNCS[step_id](paths, args)
        outputs.append(output)
        print(f"Step {step_id} wrote {display_path(output, paths.repo_root)}")
    return outputs


def main_for_step(step_id: str, description: str) -> None:
    parser = add_common_args(argparse.ArgumentParser(description=description))
    args = parser.parse_args()
    run_steps([step_id], args)
