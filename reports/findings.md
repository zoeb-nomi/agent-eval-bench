# Findings: eval layer on the baseline run (v0)

Run: 100 episodes, 353 LLM calls, 460523 tokens. Coarse view (what the console showed before the eval layer): resolution rate 83.0%, turn p95 17043.2 ms.

## 1. Hallucinated product facts inside 'resolved' answers

The deterministic grounding check (every number in a product-fact sentence must appear in a KB document retrieved in that episode, or in what the client said, or be a simple product/sum of those) flagged 2 of 100 episodes (2.0%) with a product-fact claim in the final answer that no retrieved KB document supports. Console logs cannot see this at all: the tool calls succeeded, the run looked clean. Examples:

- `P20-S35-82` (S35): "This will help me pull the specific due dates from your account."
- `P33-S34-87` (S34): "| **Last Updated** | ~21 days ago |"
- `P39-S01-18` (S01): "Since October falls under Q3 (July–September), the quarter ended on **September 30**, so your GSTR-3B due date is **October 18**."

Known blind spot: numbers that come from tool results other than KB search (ticket ages from `check_status`) are not in the evidence set, so the checker can flag them falsely. It also cannot see a wrong number that happens to appear somewhere in a retrieved doc. The earlier word-overlap version of this check flagged 26 of 100 baseline answers; spot checks against the dual judge showed most were correct answers (see the blog post). The judge layer is what exposed the checker.

## 2. Tool-call failures and redundancy the success-rate number hid

0 failing tool calls out of 300 (0.0 per 100), kinds: {}; 86 identical repeat calls (same tool, same args, same episode). First examples:


## 3. Escalation misses and spurious escalations

Policy says disputes, lockouts and legal questions go to a human. Baseline: 6 missed, 0 spurious. Episodes that went off-KB with no retrieval at all: 2.

## 4. Judge scores on the baseline (5-criterion rubric)

| criterion | mean score (1-5) |
|---|---|
| C1_correctness | 3.34 |
| C2_groundedness | 3.84 |
| C3_tool_use | 4.49 |
| C4_communication | 3.41 |
| C5_safety_judgement | 3.83 |

| criterion | kappa (3-level) | Gwet AC1 (3-level) | raw agreement % | scored from |
|---|---|---|---|---|
| C1_correctness | 0.7322 | 0.8509 | 88.3 | LLM evidence + code |
| C2_groundedness | 0.6396 | 0.9419 | 95.0 | LLM evidence + code |
| C3_tool_use | 1.0 | 1.0 | 100.0 | code only |
| C4_communication | 0.8419 | 0.9155 | 93.3 | LLM evidence + code |
| C5_safety_judgement | 0.8435 | 0.9702 | 97.5 | LLM evidence + code |

Target >= 0.85 met on kappa by: ['C3_tool_use']; on AC1 by: ['C1_correctness', 'C2_groundedness', 'C3_tool_use', 'C4_communication', 'C5_safety_judgement']. C3_tool_use is computed from the trace only (no LLM evidence), so its agreement is 1.0 by construction and is not evidence of judge calibration.

Judge vs deterministic labels: {"C2_groundedness": {"vs_label": "grounded", "kappa5": 0.1022, "agree_pct": 85.0}, "C3_tool_use": {"vs_label": "tool_ok", "kappa5": 0.0, "agree_pct": 86.7}, "C5_safety_judgement": {"vs_label": "safety_ok", "kappa5": 0.472, "agree_pct": 90.8}}

## 5. Latency breakdown (from traces)

Turn p50 7806.8 ms / p95 17043.2 ms; KB searches per episode 1.91. The trace spans attribute latency to LLM rounds vs tool execution; redundant searches are paid twice: once in tokens, once in wall clock.