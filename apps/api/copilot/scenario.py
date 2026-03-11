"""
What-if scenario agent — Task 21
POST /copilot/run-scenario
"""
from datetime import date
import json
import re
from typing import Optional
from sqlalchemy.orm import Session

from db.models import PrepPlan, ReplenishmentPlan, SKU, Outlet
from planning.prep import generate_prep_plan
from planning.replenishment import recommend_replenishment
from alerts.waste import detect_waste_risk
from alerts.stockout import detect_stockout_risk


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
    Supports: "cut X by Y%", "increase X by Y%", "add promo at OUTLET"
    Returns: {type, sku_hint, outlet_hint, pct_change}
    """
    text_lower = text.lower()
    result = {"type": "unknown", "sku_hint": None, "outlet_hint": None, "pct_change": 0}

    # look for percentage
    pct_match = re.search(r"(\d+)\s*%", text_lower)
    if pct_match:
        result["pct_change"] = int(pct_match.group(1))

    if any(word in text_lower for word in ["cut", "reduce", "decrease", "lower"]):
        result["type"] = "reduce_prep"
        result["pct_change"] = -abs(result["pct_change"])
    elif any(word in text_lower for word in ["increase", "boost", "add", "more"]):
        result["type"] = "increase_prep"
        result["pct_change"] = abs(result["pct_change"])
    elif "promo" in text_lower or "event" in text_lower:
        result["type"] = "promo_event"
        result["pct_change"] = 25  # default promo boost

    # extract SKU hint
    sku_keywords = ["croissant", "muffin", "bread", "danish", "cinnamon", "sourdough", "almond", "matcha"]
    for kw in sku_keywords:
        if kw in text_lower:
            result["sku_hint"] = kw
            break

    # extract outlet hint
    outlet_keywords = ["klcc", "bangsar", "mid valley", "midvalley", "bukit bintang", "damansara"]
    for kw in outlet_keywords:
        if kw in text_lower:
            result["outlet_hint"] = kw.replace("midvalley", "mid valley")
            break

    return result


def run_scenario_simulation(
    scenario_text: str,
    target_date: date,
    db: Session,
) -> ScenarioResult:
    """
    Simulate a what-if scenario. This is advisory only — does not modify actual plans.
    """
    # Get baseline alerts
    baseline_prep_plan = (
        db.query(PrepPlan)
        .filter(PrepPlan.plan_date == target_date)
        .order_by(PrepPlan.created_at.desc())
        .first()
    )
    if not baseline_prep_plan:
        baseline_prep_plan = generate_prep_plan(target_date, db)

    baseline_waste = detect_waste_risk(target_date, db)
    baseline_stockouts = detect_stockout_risk(target_date, db)

    intent = _parse_scenario(scenario_text)

    # Build interpretation
    if intent["type"] == "unknown":
        return ScenarioResult(
            scenario_text=scenario_text,
            baseline_waste_alerts=len(baseline_waste),
            modified_waste_alerts=len(baseline_waste),
            baseline_stockouts=len(baseline_stockouts),
            modified_stockouts=len(baseline_stockouts),
            recommendation="Could not interpret scenario. Try: 'cut croissant prep at Bangsar by 15%'",
            interpretation="Scenario could not be parsed. No changes simulated.",
        )

    # Simulate the change
    pct = intent["pct_change"] / 100.0
    sku_names = {s.name.lower(): s for s in db.query(SKU).all()}
    outlet_names = {o.name.lower(): o for o in db.query(Outlet).all()}

    target_sku = None
    target_outlet = None

    if intent["sku_hint"]:
        for name, sku in sku_names.items():
            if intent["sku_hint"] in name:
                target_sku = sku
                break

    if intent["outlet_hint"]:
        for name, outlet in outlet_names.items():
            if intent["outlet_hint"] in name.lower():
                target_outlet = outlet
                break

    # Estimate impact on alerts
    # Simple heuristic: reducing prep reduces waste alerts for that SKU/outlet,
    # but may increase stockout alerts, and vice versa.
    modified_waste = list(baseline_waste)
    modified_stockout = list(baseline_stockouts)

    if intent["type"] == "reduce_prep":
        # Fewer waste alerts for targeted SKU/outlet
        modified_waste = [
            a for a in baseline_waste
            if not (
                (target_sku is None or a.sku_name.lower() == target_sku.name.lower()) and
                (target_outlet is None or a.outlet_name.lower() == target_outlet.name.lower())
            )
        ]
        # Some stockout risk introduced
        extra_stockouts = max(0, round(abs(pct) * 3))
        interpretation = (
            f"Reducing prep by {abs(intent['pct_change'])}% could eliminate "
            f"{len(baseline_waste) - len(modified_waste)} waste alert(s) but may introduce "
            f"~{extra_stockouts} additional stockout risk(s)."
        )
        recommendation = (
            f"Proceed with caution. Recommended reduction: "
            f"{min(abs(intent['pct_change']), 10)}% to balance waste and availability."
        )

    elif intent["type"] in ("increase_prep", "promo_event"):
        # Fewer stockout alerts, possible more waste
        modified_stockout = [
            a for a in baseline_stockouts
            if not (
                (target_sku is None or a.sku_name.lower() == target_sku.name.lower()) and
                (target_outlet is None or a.outlet_name.lower() == target_outlet.name.lower())
            )
        ]
        extra_waste = max(0, round(pct * 2))
        interpretation = (
            f"Increasing prep by {intent['pct_change']}% could resolve "
            f"{len(baseline_stockouts) - len(modified_stockout)} stockout risk(s) but may add "
            f"~{extra_waste} waste alert(s)."
        )
        recommendation = (
            f"Consider increasing prep by {min(intent['pct_change'], 20)}% with close "
            f"end-of-day monitoring to prevent overproduction."
        )
    else:
        interpretation = "Scenario simulated with default assumptions."
        recommendation = "Review baseline alerts before making changes."

    return ScenarioResult(
        scenario_text=scenario_text,
        baseline_waste_alerts=len(baseline_waste),
        modified_waste_alerts=len(modified_waste),
        baseline_stockouts=len(baseline_stockouts),
        modified_stockouts=len(modified_stockout),
        recommendation=recommendation,
        interpretation=interpretation,
    )
