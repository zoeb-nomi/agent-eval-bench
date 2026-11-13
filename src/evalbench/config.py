"""Central configuration for the eval bench.

Env vars:
  OPENROUTER_API_KEY   - required for live runs (never printed).
  EVALBENCH_AGENT_MODEL / EVALBENCH_JUDGE_A / EVALBENCH_JUDGE_B - model ids.
  LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST - when all three are
  set, traces go to Langfuse; otherwise they go to a local JSONL sink with the
  same trace/span/generation schema, so the eval layer runs identically.
"""
from __future__ import annotations

import os
from pathlib import Path

AGENT_MODEL = os.environ.get("EVALBENCH_AGENT_MODEL", "z-ai/glm-4.7-flash")
JUDGE_A_MODEL = os.environ.get("EVALBENCH_JUDGE_A", "deepseek/deepseek-v4-flash")
JUDGE_B_MODEL = os.environ.get("EVALBENCH_JUDGE_B", "z-ai/glm-5.3-flash")
MAX_TOOL_ROUNDS = 6
MAX_TURNS = 4
SIM_CONCURRENCY = int(os.environ.get("EVALBENCH_SIM_CONCURRENCY", "50"))  # all 50 personas at once
RUN_SEED = 20261111

PKG_ROOT = Path(__file__).resolve().parent
DATA_DIR = PKG_ROOT / "data"
REPO_ROOT = PKG_ROOT.parent.parent


def use_langfuse() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
        and os.environ.get("LANGFUSE_HOST")
    )
