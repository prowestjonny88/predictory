"""
Compatibility wrapper for the full Predictory ML pipeline.

Prefer running individual scripts under scripts/ml_pipeline/ when iterating on
one stage. This wrapper preserves the old entrypoint while upgrading it to run
Steps 01-12 end to end.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIPELINE_DIR = Path(__file__).resolve().parent / "ml_pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

from pipeline_common import add_common_args, run_steps  # noqa: E402


def main() -> None:
    parser = add_common_args(
        argparse.ArgumentParser(description="Run the full Predictory LightGBM ML pipeline.")
    )
    parser.add_argument(
        "--through-step",
        choices=[f"{number:02d}" for number in range(1, 13)],
        default="12",
        help="Run from Step 01 through this step.",
    )
    args = parser.parse_args()
    step_ids = [f"{number:02d}" for number in range(1, int(args.through_step) + 1)]
    run_steps(step_ids, args)


if __name__ == "__main__":
    main()
