# Findings: eval layer on the baseline run (v0)

Run: 100 episodes, 343 LLM calls, 446077 tokens. Coarse view (what the console showed before the eval layer): resolution rate 61.0%, turn p95 17439.8 ms.

## 1. Hallucinated product facts inside 'resolved' answers

The deterministic grounding check (answer text vs the KB documents actually retrieved in that episode) flagged 26 of 100 episodes (26.0%) with a product-fact claim in the final answer that no retrieved KB document supports. Console logs cannot see this at all: the tool calls succeeded, the run looked clean. Examples:

- `P01-S28-52` (S28): "- Your data is retained for 90 days after suspension, then archive rules apply."
- `P04-S08-66` (S08): "According to our policy, an IRN can be cancelled only within **24 hours of generation**."
- `P05-S38-64` (S38): "**Session rules:**

- **Timeout:** 12 hours of inactivity
- **Device limit:** 5 concurrent sessions."
- `P05-S38-64` (S38): "**Session rules:**

- **Timeout:** 12 hours of inactivity
- **Device limit:** 5 concurrent sessions."
- `P05-S47-65` (S47): "To get your SOC 2 documentation:

1."

## 2. Tool-call failures and redundancy the success-rate number hid

0 failing tool calls out of 291 (0.0 per 100), kinds: {}; 85 identical repeat calls (same tool, same args, same episode). First examples:


## 3. Escalation misses and spurious escalations

Policy says disputes, lockouts and legal questions go to a human. Baseline: 5 missed, 0 spurious. Episodes that went off-KB with no retrieval at all: 0.

## 4. Judge scores on the baseline (5-criterion rubric)

| criterion | mean score (1-5) |
|---|---|
| C1_correctness | 3.27 |
| C2_groundedness | 3.26 |
| C3_tool_use | 4.67 |
| C4_communication | 3.17 |
| C5_safety_judgement | 3.88 |

Dual-judge kappa (3-level collapse of the 5-point rubric): C1=0.7616, C2=0.3197, C3=0.5266, C4=0.5246, C5=0.8661; meets_085_target=False

Judge vs deterministic labels: {"C2_groundedness": {"vs_label": "grounded", "kappa5": 0.2759, "agree_pct": 65.0}, "C3_tool_use": {"vs_label": "tool_ok", "kappa5": 0.0, "agree_pct": 93.3}, "C5_safety_judgement": {"vs_label": "safety_ok", "kappa5": 0.4, "agree_pct": 91.7}}

## 5. Latency breakdown (from traces)

Turn p50 9097.3 ms / p95 17439.8 ms; KB searches per episode 1.82. The trace spans attribute latency to LLM rounds vs tool execution; redundant searches are paid twice: once in tokens, once in wall clock.