# Before / after: baseline vs instrumented re-run

Same 50 personas, same seeded scenario deal, same model. v0: minimal prompt, guardrails observe-only. v1: policy prompt, enforced guardrails, tuned tool hints, full tracing + judge eval in the loop.

| metric | v0 baseline | v1 instrumented |
|---|---|---|
| resolution rate (%) | 61.0 | 65.0 |
| first-pass resolution (%) | 64.9 | 60.8 |
| clarify-when-vague (%) | 37.5 | 50.0 |
| injection blocked (%) | 50.0 | 100.0 |
| hallucination detected in final answers (episodes) | 26 | 32 |
| hallucination exposed to client (episodes) | 26 | 0 |
| tool-calling errors per 100 calls | 0.0 | 0.0 |
| redundant repeat tool calls | 85 | 1 |
| KB searches per episode | 1.82 | 1.75 |
| escalation: missed episodes | 5 | 2 |
| escalation: spurious episodes | 0 | 0 |
| turn latency p50 (ms) | 9097.3 | 6771.3 |
| turn latency p95 (ms) | 17439.8 | 15545.6 |

## Outcome mix

| outcome | v0 | v1 |
|---|---|---|
| answered_vague | 5 | 2 |
| clarified_ok | 3 | 4 |
| clarify_fail | 0 | 2 |
| escalated_ok | 7 | 10 |
| guard_block_fail | 3 | 0 |
| guard_block_ok | 3 | 6 |
| missed_escalation | 5 | 2 |
| resolved_ok | 48 | 45 |
| resolved_ungrounded | 26 | 29 |

## Cost of the runs themselves

v0: 343 LLM calls, 396099+49978 tokens, wall 74.8 s. v1: 310 calls, 392871+43562 tokens, wall 52.9 s.

## By category (correct-episode rate %)

| category | v0 % | v1 % |
|---|---|---|
| account | 70.0 | 70.0 |
| billing | 67.0 | 75.0 |
| calendar | 50.0 | 17.0 |
| contracts | 12.0 | 62.0 |
| e-invoicing | 67.0 | 50.0 |
| gst-filing | 71.0 | 43.0 |
| injection | 50.0 | 100.0 |
| integrations | 83.0 | 100.0 |
| itc | 100.0 | 100.0 |
| multi_issue | 25.0 | 75.0 |
| security | 0.0 | 0.0 |
| status | 100.0 | 100.0 |
| vague | 38.0 | 50.0 |