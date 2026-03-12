"""
What-if scenario agent - Task 21
POST /copilot/run-scenario
"""
from datetime import date
import re

from sqlalchemy.orm import Session

from alerts.stockout import detect_stockout_risk
from alerts.waste import detect_waste_risk
from db.models import Outlet, SKU

DEFAULT_SCENARIO_PCT = 10
DEFAULT_PROMO_PCT = 25
DAYPART_KEYWORDS = {
    "reduce": ["cut", "reduce", "decrease", "lower", "kurang", "kurangkan", "turun", "减少", "降低"],
    "increase": ["increase", "boost", "raise", "more", "tambah", "tingkatkan", "naik", "增加", "提高"],
    "promo": ["promo", "event", "promotion", "promosi", "acara", "促销", "活动"],
}


class ScenarioResult:
    def __init__(
        self,
        scenario_text: str,
        baseline_waste_alerts: int,
        modified_waste_alerts: int,
        baseline_stockouts: int,
        modified_stockouts: int,
        recommendation: str,
        interpretation: str,
    ):
        self.scenario_text = scenario_text
        self.baseline_waste_alerts = baseline_waste_alerts
        self.modified_waste_alerts = modified_waste_alerts
        self.baseline_stockouts = baseline_stockouts
        self.modified_stockouts = modified_stockouts
        self.recommendation = recommendation
        self.interpretation = interpretation

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario_text,
            "baseline": {
                "waste_alerts": self.baseline_waste_alerts,
                "stockout_alerts": self.baseline_stockouts,
            },
            "modified": {
                "waste_alerts": self.modified_waste_alerts,
                "stockout_alerts": self.modified_stockouts,
            },
            "delta": {
                "waste_change": self.modified_waste_alerts - self.baseline_waste_alerts,
                "stockout_change": self.modified_stockouts - self.baseline_stockouts,
            },
            "recommendation": self.recommendation,
            "interpretation": self.interpretation,
        }


def _parse_scenario(text: str) -> dict:
    """
    Extract intent from natural language scenario.
    Supports: "cut X by Y%", "increase X by Y%", "promo at OUTLET"
    Returns: {type, sku_hint, outlet_hint, pct_change}
    """
    text_lower = text.lower()
    result = {"type": "unknown", "sku_hint": None, "outlet_hint": None, "pct_change": 0}

    pct_match = re.search(r"(\d+)\s*%", text_lower)
    if pct_match:
        result["pct_change"] = int(pct_match.group(1))

    if any(word in text_lower for word in DAYPART_KEYWORDS["promo"]):
        result["type"] = "promo_event"
        result["pct_change"] = result["pct_change"] or DEFAULT_PROMO_PCT
    elif any(word in text_lower for word in DAYPART_KEYWORDS["reduce"]):
        result["type"] = "reduce_prep"
        result["pct_change"] = -abs(result["pct_change"] or DEFAULT_SCENARIO_PCT)
    elif any(word in text_lower for word in DAYPART_KEYWORDS["increase"]):
        result["type"] = "increase_prep"
        result["pct_change"] = abs(result["pct_change"] or DEFAULT_SCENARIO_PCT)

    sku_keywords = ["croissant", "muffin", "bread", "danish", "cinnamon", "sourdough", "almond", "matcha"]
    for keyword in sku_keywords:
        if keyword in text_lower:
            result["sku_hint"] = keyword
            break

    outlet_keywords = ["klcc", "bangsar", "mid valley", "midvalley", "bukit bintang", "damansara"]
    for keyword in outlet_keywords:
        if keyword in text_lower:
            result["outlet_hint"] = keyword.replace("midvalley", "mid valley")
            break

    return result


def _build_scope_label(target_sku, target_outlet) -> str:
    if target_sku and target_outlet:
        return f"{target_sku.name} at {target_outlet.name}"
    if target_sku:
        return target_sku.name
    if target_outlet:
        return target_outlet.name
    return "the selected plan"


def _matching_count(alerts, target_sku, target_outlet) -> int:
    matches = 0
    for alert in alerts:
        if target_sku and alert.sku_id != target_sku.id:
            continue
        if target_outlet and alert.outlet_id != target_outlet.id:
            continue
        if target_sku or target_outlet:
            matches += 1
    return matches


def run_scenario_simulation(
    scenario_text: str,
    target_date: date,
    db: Session,
    language: str = "en",
) -> ScenarioResult:
    """
    Simulate a what-if scenario. This is advisory only - it does not modify plans.
    """
    baseline_waste = detect_waste_risk(target_date, db)
    baseline_stockouts = detect_stockout_risk(target_date, db)

    intent = _parse_scenario(scenario_text)
    if intent["type"] == "unknown":
        if language == "ms":
            recommendation = "Senario tidak dapat ditafsir. Cuba: 'kurangkan prep croissant di Bangsar sebanyak 15%'"
            interpretation = "Senario tidak dapat dihuraikan. Tiada perubahan disimulasikan."
        elif language == "zh-CN":
            recommendation = "无法识别该情景。可尝试：'将 Bangsar 的 croissant 备货减少 15%'"
            interpretation = "情景无法解析，因此未模拟任何变化。"
        else:
            recommendation = "Could not interpret scenario. Try: 'cut croissant prep at Bangsar by 15%'"
            interpretation = "Scenario could not be parsed. No changes simulated."
        return ScenarioResult(
            scenario_text=scenario_text,
            baseline_waste_alerts=len(baseline_waste),
            modified_waste_alerts=len(baseline_waste),
            baseline_stockouts=len(baseline_stockouts),
            modified_stockouts=len(baseline_stockouts),
            recommendation=recommendation,
            interpretation=interpretation,
        )

    pct = abs(intent["pct_change"]) / 100.0
    sku_names = {sku.name.lower(): sku for sku in db.query(SKU).all()}
    outlet_names = {outlet.name.lower(): outlet for outlet in db.query(Outlet).all()}

    target_sku = None
    target_outlet = None

    if intent["sku_hint"]:
        for name, sku in sku_names.items():
            if intent["sku_hint"] in name:
                target_sku = sku
                break

    if intent["outlet_hint"]:
        for name, outlet in outlet_names.items():
            if intent["outlet_hint"] in name:
                target_outlet = outlet
                break

    scope_label = _build_scope_label(target_sku, target_outlet)
    baseline_waste_count = len(baseline_waste)
    baseline_stockout_count = len(baseline_stockouts)
    scoped_waste_count = _matching_count(baseline_waste, target_sku, target_outlet)
    scoped_stockout_count = _matching_count(baseline_stockouts, target_sku, target_outlet)

    modified_waste_count = baseline_waste_count
    modified_stockout_count = baseline_stockout_count

    if intent["type"] == "reduce_prep":
        resolved_waste = scoped_waste_count or (1 if baseline_waste_count > 0 else 0)
        extra_stockouts = max(0, round(pct * 3))
        modified_waste_count = max(0, baseline_waste_count - resolved_waste)
        modified_stockout_count = baseline_stockout_count + extra_stockouts
        if language == "ms":
            interpretation = (
                f"Mengurangkan prep untuk {scope_label} sebanyak {abs(intent['pct_change'])}% "
                f"boleh mengurangkan {resolved_waste} amaran pembaziran tetapi mungkin menambah "
                f"kira-kira {extra_stockouts} risiko kehabisan stok."
            )
            recommendation = (
                f"Teruskan dengan berhati-hati untuk {scope_label}. Cadangan pengurangan: "
                f"{min(abs(intent['pct_change']), 10)}% bagi mengimbangi pembaziran dan ketersediaan."
            )
        elif language == "zh-CN":
            interpretation = (
                f"将 {scope_label} 的备货减少 {abs(intent['pct_change'])}% 可能减少 {resolved_waste} 条"
                f"浪费预警，但也可能新增约 {extra_stockouts} 条缺货风险。"
            )
            recommendation = (
                f"建议谨慎执行 {scope_label} 的调整。推荐减幅为 {min(abs(intent['pct_change']), 10)}%，"
                f"以平衡浪费与供应可得性。"
            )
        else:
            interpretation = (
                f"Reducing prep for {scope_label} by {abs(intent['pct_change'])}% could remove "
                f"{resolved_waste} waste alert(s) but may introduce about {extra_stockouts} "
                f"additional stockout risk(s)."
            )
            recommendation = (
                f"Proceed with caution for {scope_label}. Recommended reduction: "
                f"{min(abs(intent['pct_change']), 10)}% to balance waste and availability."
            )
    else:
        resolved_stockouts = scoped_stockout_count or (1 if baseline_stockout_count > 0 else 0)
        extra_waste = max(0, round(pct * 2))
        modified_stockout_count = max(0, baseline_stockout_count - resolved_stockouts)
        modified_waste_count = baseline_waste_count + extra_waste
        if language == "ms":
            interpretation = (
                f"Meningkatkan prep untuk {scope_label} sebanyak {abs(intent['pct_change'])}% "
                f"boleh mengurangkan {resolved_stockouts} risiko kehabisan stok tetapi mungkin "
                f"menambah kira-kira {extra_waste} amaran pembaziran."
            )
            recommendation = (
                f"Pertimbangkan peningkatan prep untuk {scope_label} sebanyak "
                f"{min(abs(intent['pct_change']), 20)}% dengan pemantauan rapi pada akhir hari."
            )
        elif language == "zh-CN":
            interpretation = (
                f"将 {scope_label} 的备货增加 {abs(intent['pct_change'])}% 可能减少 {resolved_stockouts} 条"
                f"缺货风险，但也可能新增约 {extra_waste} 条浪费预警。"
            )
            recommendation = (
                f"可考虑将 {scope_label} 的备货增加 {min(abs(intent['pct_change']), 20)}%，"
                f"并在营业结束前密切监控，以避免过量生产。"
            )
        else:
            interpretation = (
                f"Increasing prep for {scope_label} by {abs(intent['pct_change'])}% could remove "
                f"{resolved_stockouts} stockout risk(s) but may add about {extra_waste} waste alert(s)."
            )
            recommendation = (
                f"Consider increasing prep for {scope_label} by {min(abs(intent['pct_change']), 20)}% "
                f"with close end-of-day monitoring to prevent overproduction."
            )

    return ScenarioResult(
        scenario_text=scenario_text,
        baseline_waste_alerts=baseline_waste_count,
        modified_waste_alerts=modified_waste_count,
        baseline_stockouts=baseline_stockout_count,
        modified_stockouts=modified_stockout_count,
        recommendation=recommendation,
        interpretation=interpretation,
    )
