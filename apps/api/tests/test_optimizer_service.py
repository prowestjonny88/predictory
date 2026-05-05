from services.optimizer import calculate_optimal_prep


def test_optimizer_respects_batch_rounding_and_exposure_fields():
    decision = calculate_optimal_prep(
        p10=80,
        p50=100,
        p90=125,
        opening_stock=12,
        unit_price=10,
        unit_cost=3,
        batch_size=5,
    )

    assert decision["recommended_prep"] % 5 == 0
    assert decision["financial_exposure"]["stockout_exposure_rm"] >= 0
    assert decision["financial_exposure"]["waste_exposure_rm"] >= 0
    assert decision["expected_stockout_units"] >= 0
    assert decision["expected_waste_units"] >= 0


def test_optimizer_moves_above_expected_when_stockout_cost_is_high():
    decision = calculate_optimal_prep(
        p10=80,
        p50=100,
        p90=130,
        opening_stock=0,
        unit_price=12,
        unit_cost=2,
        batch_size=1,
    )

    assert decision["critical_ratio"] > 0.6
    assert decision["target_demand"] > 100


def test_optimizer_applies_capacity_constraint():
    decision = calculate_optimal_prep(
        p10=80,
        p50=100,
        p90=130,
        opening_stock=0,
        unit_price=12,
        unit_cost=2,
        batch_size=5,
        capacity=90,
    )

    assert decision["recommended_prep"] == 90
    assert "capacity_limit" in decision["constraints_applied"]
