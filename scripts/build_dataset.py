"""Build the HuggingFace-ready dataset copy from a simulation run.

Usage: python scripts/build_dataset.py [run_dir ...]   (default: runs/baseline_v0 runs/instrumented_v1)
Writes dataset/ with:
  data/episodes.jsonl   one record per episode: dialogue, tool calls, retrieved
                        docs, outcome, guardrail events, judge scores
  data/scenarios.jsonl  the 50 scenario definitions (answer key + policy expectations)
  data/kb_docs.jsonl    the 26 KB documents
  README.md             HuggingFace dataset card (overwrite-safe: repo README stays)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "evalbench"


def _scores(eval_dir: Path) -> dict:
    scores: dict[str, list] = {}
    for name in ("judge_a.jsonl", "judge_b.jsonl"):
        p = eval_dir / name
        if p.exists():
            for line in open(p):
                r = json.loads(line)
                if r.get("scores"):
                    scores.setdefault(r["item_id"], []).append(
                        {"judge": r["judge_model"], **r["scores"]})
    return scores


def main() -> None:
    runs = [Path(a) for a in sys.argv[1:]] or [ROOT / "runs" / "baseline_v0",
                                             ROOT / "runs" / "instrumented_v1"]
    out = ROOT / "dataset"
    (out / "data").mkdir(parents=True, exist_ok=True)
    summary = {}
    n_scores = 0
    with open(out / "data" / "episodes.jsonl", "w") as f:
        for run_dir in runs:
            eval_dir = run_dir.parent / "evalset" / run_dir.name
            metrics = json.load(open(run_dir / "metrics.json"))
            cal_path = eval_dir / "calibration.json"
            cal = json.load(open(cal_path)) if cal_path.exists() else {}
            scores = _scores(eval_dir)
            n_scores += sum(len(v) for v in scores.values())
            for line in open(run_dir / "episodes.jsonl"):
                ep = json.loads(line)
                ep["run"] = run_dir.name
                ep["judge_scores"] = [
                    {"item_id": k, **v} for k, vals in scores.items()
                    for v in vals if k.split(":")[0] == ep["episode_id"]]
                f.write(json.dumps(ep, ensure_ascii=False) + "\n")
            summary[run_dir.name] = {
                "episodes": metrics["episodes"],
                "resolution_rate": metrics["resolution_rate"],
                "hallucination_exposed_pct": metrics["hallucination"]["exposed_rate_pct"],
                "missed_escalations": metrics["escalation"]["missed"],
                "redundant_repeat_calls": metrics["tools"]["redundant_repeat_calls"],
                "dual_judge_kappa3": {k: v["kappa3"] for k, v in
                                      cal.get("dual_judge_kappa", {}).items()},
            }
    with open(out / "data" / "scenarios.jsonl", "w") as f:
        for s in yaml.safe_load(open(PKG / "data" / "scenarios.yaml")):
            f.write(json.dumps(s, ensure_ascii=False, default=str) + "\n")
    with open(out / "data" / "kb_docs.jsonl", "w") as f:
        for d in yaml.safe_load(open(PKG / "data" / "kb_docs.yaml")):
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
    n_eps = sum(v["episodes"] for v in summary.values())
    headline = json.dumps(summary, indent=2)

    card = f"""---
license: cc-by-4.0
task_categories:
- text-generation
language: [en]
tags:
- agent-evaluation
- llm-judge
- support-agent
- guardrails
size_categories:
- n<1K
---

# LedgerLane support-agent eval episodes (baseline v0 + instrumented v1)

Simulated support episodes for evaluating a LangGraph support-ticket agent:
50 client personas x 2 episodes per run, {n_eps} episodes across two runs, over a legal-tech
compliance KB (GST filings, e-invoicing, contracts, billing, integrations).

The client side is a deterministic, seeded state machine (no LLM), so episodes are
reproducible and every token is attributable to the agent under test.

## Contents

- `data/episodes.jsonl` — one record per episode: scenario, dialogue turns, tool
  calls with results, retrieved KB doc ids, guardrail events, outcome label,
  latency, and the 5-criterion LLM-judge scores (two judge models).
- `data/scenarios.jsonl` — the 50 scenario definitions with the expected behaviour
  and the answer-key KB documents.
- `data/kb_docs.jsonl` — the 26 KB documents the agent retrieves from.

## Outcome labels

`resolved_ok`, `resolved_ungrounded`, `clarified_ok`, `escalated_ok`,
`missed_escalation`, `spurious_escalation`, `guard_block_ok`, `guard_block_fail`,
`answered_vague`, `answered_without_kb`.

## Headline numbers per run

Each episode carries `run` (`baseline_v0` = minimal prompt, guardrails observe
only; `instrumented_v1` = policy prompt, guardrails enforce).

```json
{headline}
```

Intended use: benchmarking support agents, judge-rubric calibration research,
guardrail evaluation. Not a production conversation log.
"""
    (out / "README.md").write_text(card)
    print(f"wrote {out}/data/*.jsonl and {out}/README.md "
          f"({n_eps} episodes, {n_scores} judge scores)")


if __name__ == "__main__":
    main()
