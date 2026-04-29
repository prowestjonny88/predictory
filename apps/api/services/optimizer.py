"""
Financial optimizer service — calculates optimal prep quantities
"""
from typing import Dict, Any, Optional
import math


def calculate_optimal_prep(
    p10: float,
    p50: float,
    p90: float,
    opening_stock: float,
    unit_price: float,
    unit_cost: float,
    batch_size: int = 5,
    capacity: Optional[int] = None,
    freshness_hours: int = 8,
) -> Dict[str, Any]:
    """
    Calculate optimal prep quantity using financial optimization.

    Args:
        p10: 10th percentile demand estimate
        p50: 50th percentile (median) demand estimate
        p90: 90th percentile demand estimate
        opening_stock: Current stock available
        unit_price: Selling price per unit
        unit_cost: Cost per unit
        batch_size: Production batch size
        capacity: Maximum prep capacity
        freshness_hours: Shelf life in hours

    Returns:
        Dict with recommended_prep, financial_exposure, rationale
    """
    if unit_price <= 0 or unit_cost <= 0:
        return {
            "recommended_prep": 0,
            "financial_exposure": {"stockout_exposure_rm": 0, "waste_exposure_rm": 0},
            "reason_summary": "Invalid pricing data",
            "batch_size": batch_size,
        }

    # Calculate cost parameters
    waste_cost = unit_cost  # Assume salvage value = 0 for simplicity
    stockout_cost = unit_price - unit_cost

    if stockout_cost <= 0:
        # No profit margin, prep conservatively
        recommended_demand_level = p50
    else:
        # Critical ratio method
        critical_ratio = stockout_cost / (stockout_cost + waste_cost)

        # Interpolate demand level based on critical ratio
        if critical_ratio <= 0.1:
            recommended_demand_level = p10
        elif critical_ratio >= 0.9:
            recommended_demand_level = p90
        else:
            # Linear interpolation between p10 and p90
            ratio = (critical_ratio - 0.1) / 0.8
            recommended_demand_level = p10 + ratio * (p90 - p10)

    # Adjust for opening stock
    net_demand = max(0, recommended_demand_level - opening_stock)

    # Apply batch size rounding
    if batch_size > 1:
        recommended_prep = math.ceil(net_demand / batch_size) * batch_size
    else:
        recommended_prep = math.ceil(net_demand)

    # Apply capacity constraint
    if capacity and recommended_prep > capacity:
        recommended_prep = capacity

    # Calculate financial exposure
    stockout_exposure = stockout_cost * max(0, p50 - opening_stock - recommended_prep)
    waste_exposure = waste_cost * max(0, recommended_prep + opening_stock - p10)

    # Determine reason
    if stockout_cost > waste_cost:
        reason = "Stockout cost is higher than waste cost, so prep is slightly above expected demand."
    else:
        reason = "Waste cost is higher than stockout cost, so prep is conservative."

    return {
        "recommended_prep": recommended_prep,
        "financial_exposure": {
            "stockout_exposure_rm": round(stockout_exposure, 2),
            "waste_exposure_rm": round(waste_exposure, 2),
        },
        "reason_summary": reason,
        "batch_size": batch_size,
        "critical_ratio": round(critical_ratio, 3) if 'critical_ratio' in locals() else None,
        "recommended_demand_level": round(recommended_demand_level, 1),
    }