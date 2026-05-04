# Predictory ML Pipeline

This folder contains the lightweight repo-native compatibility pipeline for the
Predictory demo. The accepted demo artifacts currently committed in
`backend/models/` and `apps/web/public/demo-data/` were generated from the fuller
Kaggle workflow and then integrated into the repo.

The scripts here are intentionally runnable from the repository, but they are
not yet expected to reproduce exact Kaggle artifact parity. In particular,
Steps 05-11 still use simplified operational simulation, demand recovery,
residual-band logic, and prep optimization.

Do not overwrite the accepted artifacts in `backend/models/` or
`apps/web/public/demo-data/` unless you are intentionally regenerating and
revalidating the demo bundle.

Recommended upgrade order:

1. Upgrade `05_simulate_ops.py` / `pipeline_common.step_05_simulate_ops` with
   stock-aware prep, opening stock, carryover, and material waste/stockout flags.
2. Upgrade `06_recover_demand.py` with velocity + historical + capped stockout
   recovery.
3. Upgrade `07_build_features.py` toward the richer accepted feature schema.
4. Upgrade `08_train_model.py` with model sweep, Tweedie selection, and complete
   metrics output.
5. Upgrade `09_build_bands.py` with the full fallback hierarchy.
6. Upgrade `11_optimize_prep.py` with scenario expected-cost optimization,
   capacity, batch, minimum display, and freshness constraints.
7. Add BOM and ingredient simulation once metrics and optimizer fidelity are
   stable.
