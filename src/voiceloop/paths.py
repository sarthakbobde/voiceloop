"""Every file and folder the project reads or writes, defined once.

ROOT is found from this file's own location, so it works from any working directory.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONFIGS = ROOT / "configs"
MODELS_CONFIG = CONFIGS / "models.yaml"

DATA = ROOT / "data"
MODELS = ROOT / "models"  # downloaded weights (git-ignored)

EVALS = ROOT / "evals"
EVAL_RUNS = EVALS / "runs"  # raw latency / turn logs (git-ignored)
EVAL_REPORTS = EVALS / "reports"  # summarised reports (committed)
