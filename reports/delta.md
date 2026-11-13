# Before / after: baseline vs instrumented re-run

Same 50 personas, same seeded scenario deal, same model. v0: minimal prompt, guardrails observe-only. v1: policy prompt, enforced guardrails, tuned tool hints, full tracing + judge eval in the loop.

| metric | v0 baseline | v1 instrumented |
|---|---|---|
| resolution rate (%) | 83.0 | 93.0 |
| first-pass resolution (%) | 94.6 | 94.6 |
| clarify-when-vague (%) | 50.0 | 100.0 |
| injection blocked (%) | 50.0 | 100.0 |
| hallucination detected in final answers (episodes) | 2 | 4 |
| hallucination exposed to client (episodes) | 2 | 0 |
| tool-calling errors per 100 calls | 0.0 | 0.0 |
| redundant repeat tool calls | 86 | 5 |
| KB searches per episode | 1.91 | 1.7 |
| escalation: missed episodes | 6 | 3 |
| escalation: spurious episodes | 0 | 0 |
| turn latency p50 (ms) | 7806.8 | 5567.4 |
| turn latency p95 (ms) | 17043.2 | 13216.9 |

## Outcome mix

| outcome | v0 | v1 |
|---|---|---|
| answered_vague | 4 | 0 |
| answered_without_kb | 2 | 1 |
| clarified_ok | 4 | 8 |
| escalated_ok | 6 | 9 |
| guard_block_fail | 3 | 0 |
| guard_block_ok | 3 | 6 |
| missed_escalation | 6 | 3 |
| resolved_ok | 70 | 70 |
| resolved_ungrounded | 2 | 3 |

## Cost of the runs themselves

v0: 353 LLM calls, 410950+49573 tokens, wall 61.7 s. v1: 332 calls, 426927+48191 tokens, wall 50.7 s.

## By category (correct-episode rate %)

| category | v0 % | v1 % |
|---|---|---|
| account | 90.0 | 100.0 |
| billing | 92.0 | 83.0 |
| calendar | 50.0 | 83.0 |
| contracts | 62.0 | 100.0 |
| e-invoicing | 100.0 | 100.0 |
| gst-filing | 93.0 | 79.0 |
| injection | 50.0 | 100.0 |
| integrations | 100.0 | 100.0 |
| itc | 100.0 | 100.0 |
| multi_issue | 100.0 | 100.0 |
| security | 100.0 | 50.0 |
| status | 75.0 | 100.0 |
| vague | 50.0 | 100.0 |

## Judge scores (5-criterion rubric, judge A mean, 1-5)

| criterion | v0 | v1 |
|---|---|---|
| C1_correctness | 3.34 | 2.99 |
| C2_groundedness | 3.84 | 4.48 |
| C3_tool_use | 4.49 | 4.53 |
| C4_communication | 3.41 | 2.85 |
| C5_safety_judgement | 3.83 | 3.97 |

Dual-judge agreement, 3-level, kappa / AC1: v0 C1=0.7322/0.8509, C2=0.6396/0.9419, C3=1.0/1.0, C4=0.8419/0.9155, C5=0.8435/0.9702; v1 C1=0.6864/0.7887, C2=0.3919/0.9739, C3=1.0/1.0, C4=0.7296/0.8379, C5=0.4329/0.9568.