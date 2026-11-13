---
license: cc-by-4.0
task_categories:
- text-generation
language: en
pretty_name: LedgerLane support-agent eval episodes
tags:
- agent-evaluation
- llm-judge
- support-agent
- guardrails
size_categories:
- n<1K
configs:
- config_name: episodes
  data_files: data/episodes.jsonl
  default: true
- config_name: scenarios
  data_files: data/scenarios.jsonl
- config_name: kb_docs
  data_files: data/kb_docs.jsonl
---

# LedgerLane support-agent eval episodes (baseline v0 + instrumented v1)

Simulated support episodes for evaluating a LangGraph support-ticket agent:
50 client personas x 2 episodes per run, 200 episodes across two runs, over a legal-tech
compliance KB (GST filings, e-invoicing, contracts, billing, integrations).

The client side is a deterministic, seeded state machine (no LLM), so episodes are
reproducible and every token is attributable to the agent under test.

## Contents

- `data/episodes.jsonl`: one record per episode: scenario, dialogue turns, tool
  calls with results, retrieved KB doc ids, guardrail events, outcome label,
  latency, and the 5-criterion LLM-judge scores (two judge models).
- `data/scenarios.jsonl`: the 50 scenario definitions with the expected behaviour
  and the answer-key KB documents.
- `data/kb_docs.jsonl`: the 26 KB documents the agent retrieves from.

## Outcome labels

`resolved_ok`, `resolved_ungrounded`, `clarified_ok`, `escalated_ok`,
`missed_escalation`, `spurious_escalation`, `guard_block_ok`, `guard_block_fail`,
`answered_vague`, `answered_without_kb`.

## Headline numbers per run

Each episode carries `run` (`baseline_v0` = minimal prompt, guardrails observe
only; `instrumented_v1` = policy prompt, guardrails enforce).

```json
{
  "baseline_v0": {
    "episodes": 100,
    "resolution_rate": 83.0,
    "hallucination_exposed_pct": 2.0,
    "missed_escalations": 6,
    "redundant_repeat_calls": 86,
    "dual_judge_kappa3": {
      "C1_correctness": 0.7322,
      "C2_groundedness": 0.6396,
      "C3_tool_use": 1.0,
      "C4_communication": 0.8419,
      "C5_safety_judgement": 0.8435
    }
  },
  "instrumented_v1": {
    "episodes": 100,
    "resolution_rate": 93.0,
    "hallucination_exposed_pct": 0.0,
    "missed_escalations": 3,
    "redundant_repeat_calls": 5,
    "dual_judge_kappa3": {
      "C1_correctness": 0.6864,
      "C2_groundedness": 0.3919,
      "C3_tool_use": 1.0,
      "C4_communication": 0.7296,
      "C5_safety_judgement": 0.4329
    }
  }
}
```

Intended use: benchmarking support agents, judge-rubric calibration research,
guardrail evaluation. Not a production conversation log.
