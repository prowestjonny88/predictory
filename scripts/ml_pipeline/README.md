# Predictory ML Pipeline

This folder contains the lightweight repo-native compatibility pipeline for Predictory model training and artifact generation.

The runtime backend consumes the artifacts in `backend/models/`:

- `lightgbm_p50_v1.pkl`
- `model.pkl`
- `feature_schema_v1.json`
- `encoded_feature_schema_step8.json`
- `model_metrics_v1.json`
- `residual_bands_v1.json`

The scripts are runnable from the repository, but they are not expected to reproduce exact Kaggle parity yet. Training `--seed` values remain only as reproducibility controls for ML experiments; they are not runtime data setup.

Recommended upgrade order:

1. Upgrade `05_simulate_ops.py` with stock-aware prep, opening stock, carryover, and material waste/stockout flags.
2. Upgrade `06_recover_demand.py` with velocity, historical, and capped stockout recovery.
3. Upgrade `07_build_features.py` toward the richer accepted feature schema.
4. Upgrade `08_train_model.py` with model sweep, Tweedie selection, and complete metrics output.
5. Upgrade `09_build_bands.py` with the full residual hierarchy.
6. Upgrade `11_optimize_prep.py` with scenario expected-cost optimization, capacity, batch, minimum display, and freshness constraints.
7. Add BOM and ingredient simulation once metrics and optimizer fidelity are stable.
