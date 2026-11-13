# PRD: agent-eval-bench

Repo: github.com/zoeb-nomi/agent-eval-bench. Status: two seeded runs (v0, v1) committed.

## 1. Problem

Teams shipping support or compliance agents watch resolution rate and latency, and both can look healthy while the agent is wrong. In the committed baseline, tool calls had 0 errors and 83% of episodes resolved, yet 86 identical repeat calls, 6 missed escalations and 3 injection failures sat underneath. The question the bench answers: what does an eval layer catch that normal testing does not? Cost today: failures reach clients unseen, and a fix cannot be shown to help.

## 2. Users and use cases

1. **Support-agent team** compares a prompt or guardrail change before and after on the same 100 episodes.
2. **Compliance-agent team** checks that disputes, lockouts and legal questions go to a human, and that injected instructions are refused.
3. **Eval owner** tests whether their LLM judge can be trusted by running two judge families and measuring agreement.

## 3. Goals and success metrics

| Metric | Today (v0 to v1) | Target |
|---|---|---|
| Resolution rate | 83% to 93% (reports/delta.md) | Gain with a CI excluding 0; now +1.0 to +19.0 pp, exact McNemar p 0.053 (reports/bootstrap.json) |
| Injection attempts blocked | 50% to 100%, n=6 (reports/delta.md) | Larger n; exact test p 0.25 now |
| Missed escalations | 6 to 3 (reports/delta.md) | 0 |
| Identical repeat tool calls | 86 to 5 (reports/delta.md) | Near 0 |
| Ungrounded answers reaching client | 2 to 0 (reports/delta.md) | 0 |
| Judge agreement, Cohen's kappa | Only C3 (code) reaches 0.85 (reports/findings.md, README.md) | 0.85 or higher per criterion |
| Judge agreement, Gwet AC1 | All five criteria at 0.85 or higher on v0 (reports/findings.md); C1 and C4 below on v1 (README.md) | All criteria on both runs |
| Run-to-run noise | Not measured yet (one seeded run per version) | Repeat runs with spread reported |
| Cost per cycle | 460,523 tokens on v0 (reports/findings.md); a few dollars (README.md) | Keep per-run usage in metrics.json |

## 4. Non-goals

- Not a production traffic monitor or a general benchmark of models.
- Not a claim that v1 is better on every segment: v1 fixed 16 episodes and broke 6 (reports/failure_analysis.md).
- No LLM client simulator; no production-sized knowledge base.

## 5. Solution

LedgerLane, a LangGraph support agent with six tools and a guardrail layer, run as v0 (observe-only guards, minimal prompt) and v1 (enforced guards, policy prompt). 50 personas times 2 episodes give 100 episodes per run. Metrics, traces and judge scores come from the saved runs.

Design decisions and trade-offs:
- **Seeded state-machine simulator, not an LLM client.** Reproducible and cost is attributable to the agent. Cost: clients are less lifelike, and results cover this scenario set only.
- **Extract-then-score judges.** Models extract evidence as JSON; Python applies the rubric. This is what raised agreement (free-form scoring gave kappa 0.15 to 0.48). Cost: the rubric encodes my choices, and abstaining scores like a wrong answer, which lowered v1 correctness (3.34 to 2.99).
- **Two judge families.** Agreement is a real check. Cost: two sets of quirks to handle.
- **Number-based grounding check.** Replaced a word-overlap check that flagged 26 of 100 answers, most of them correct. Cost: it misses wrong numbers that appear elsewhere in a retrieved doc.
- **Paired bootstrap and exact test, reported as measured.** Honest about small samples. Cost: weaker headline claims.

## 6. Risks and mitigations

- **Judge disagreement.** Kappa misses 0.85 on most criteria. Mitigation: report AC1 alongside kappa, rescore from saved extractions.
- **Small samples.** Injection result rests on 6 episodes. Mitigation: show exact tests, add scenarios.
- **Checker blind spots.** Grounding cannot see numbers from non-KB tool results. Mitigation: documented, extend evidence set.
- **Model drift.** Judge or agent model changes alter scores. Mitigation: pin model ids, keep saved extractions and usage files.
- **Keyword escalation guard.** Refund-window and tax-advice cases slip past (3 in v1).

## 7. Roadmap

**Now**
- Repeat each version several times and report run-to-run spread.
- Add injection and escalation scenarios until the exact test can decide.
- Close the 3 remaining missed escalations.

**Next**
- Replace the keyword escalation guard with a better classifier and re-measure.
- Raise kappa on C2 and C5 for v1.
- Exercise the Langfuse path live.

**Later**
- Record per-episode token cost, not only run totals.
- Swap in a second agent and compare.
- Grow the 26-document knowledge base toward a realistic corpus.

## 8. Open questions

- Should abstention be scored as correct when the knowledge base has no answer?
- What agreement level is enough to trust a judge: kappa, AC1, or agreement with human labels?
- How many episodes does a decision need for a given effect size?
- Is the persona mix close enough to real tickets to generalise?
