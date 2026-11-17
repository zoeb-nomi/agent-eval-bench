# Arabic gap per model

> **Not for quotation.** No Arabic reader has checked the Arabic questions, reference answers or any judgement yet. No human has labelled any model answer. Treat every number as a draft.

Run date 2026-11-17. Models via OpenRouter, temperature 0. Judge: `anthropic/claude-sonnet-5.5` (live model). Cross-check judge: `deepseek/deepseek-v4.1-flash-1017`.
Gap = English accuracy minus Arabic accuracy, in percentage points, on the same paired questions (positive = worse in Arabic). Denominator = paired questions (answers judged).

Tracks: **gov** = 19 UAE government-service questions, closed-book (no page given); **consumer** = 20 returns/delivery/refund questions, answered from the supplied public help-page text (reading in the question's language, so it measures Arabic comprehension and writing, not memory). With 19-20 items per cell one question is about 5 points: gaps under about 10 points are noise.

## Strict accuracy (only `correct` counts), judge `anthropic/claude-sonnet-5.5`

| model | track | English | Arabic | gap |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | gov | 11% (2/19) | 11% (2/19) | +0 pts |
| anthropic/claude-haiku-5.5 | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| openai/gpt-6.1-terra | gov | 37% (7/19) | 42% (8/19) | -5 pts |
| openai/gpt-6.1-terra | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| deepseek/deepseek-v4.1-flash-1017 | gov | 32% (6/19) | 21% (4/19) | +11 pts |
| deepseek/deepseek-v4.1-flash-1017 | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| qwen/qwen4-max | gov | 63% (12/19) | 42% (8/19) | +21 pts |
| qwen/qwen4-max | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| mistralai/mistral-large-4-0 | gov | 21% (4/19) | 11% (2/19) | +11 pts |
| mistralai/mistral-large-4-0 | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| moonshotai/kimi-k3.1-pro | gov | 42% (8/19) | 37% (7/19) | +5 pts |
| moonshotai/kimi-k3.1-pro | consumer | 100% (20/20) | 100% (20/20) | +0 pts |

## Partial credit (correct = 1, partial = 0.5), judge `anthropic/claude-sonnet-5.5`

| model | track | English | Arabic | gap |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | gov | 37% (7/19) | 42% (8/19) | -5 pts |
| anthropic/claude-haiku-5.5 | consumer | 100% (20/20) | 98% (19.5/20) | +2 pts |
| openai/gpt-6.1-terra | gov | 66% (12.5/19) | 68% (13/19) | -3 pts |
| openai/gpt-6.1-terra | consumer | 100% (20/20) | 98% (19.5/20) | +2 pts |
| deepseek/deepseek-v4.1-flash-1017 | gov | 61% (11.5/19) | 53% (10/19) | +8 pts |
| deepseek/deepseek-v4.1-flash-1017 | consumer | 100% (20/20) | 98% (19.5/20) | +2 pts |
| qwen/qwen4-max | gov | 74% (14/19) | 63% (12/19) | +11 pts |
| qwen/qwen4-max | consumer | 100% (20/20) | 98% (19.5/20) | +2 pts |
| mistralai/mistral-large-4-0 | gov | 42% (8/19) | 39% (7.5/19) | +3 pts |
| mistralai/mistral-large-4-0 | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| moonshotai/kimi-k3.1-pro | gov | 61% (11.5/19) | 58% (11/19) | +3 pts |
| moonshotai/kimi-k3.1-pro | consumer | 100% (20/20) | 100% (20/20) | +0 pts |

## Judge agreement

- **Against human labels: not measurable yet.** The 15 'labelled' items shipped with this set were labelled `automated (from source text)` and score the reference answers, not model answers. No human-labelled model answers exist. `results/human_label_sheet.csv` lists a sample of answers with the judge's verdict and an empty column for a person (ideally an Arabic reader) to fill; once filled, agreement can be computed against it.
- Live judge vs second live judge (`deepseek/deepseek-v4.1-flash-1017`), exact verdict match: all 406/468 (87%); English 204/234 (87%); Arabic 202/234 (86%). Two models agreeing is not the same as a human agreeing.
- Unparsed judge replies (counted as incorrect): 0 of 468 (main judge), 36 of 468 (second).
- The earlier 91% figure came from a synthetic scoring script that called no model; it has been removed.

## Same strict table under the second judge (`deepseek/deepseek-v4.1-flash-1017`)

| model | track | English | Arabic | gap |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | gov | 11% (2/19) | 5% (1/19) | +5 pts |
| anthropic/claude-haiku-5.5 | consumer | 95% (19/20) | 90% (18/20) | +5 pts |
| openai/gpt-6.1-terra | gov | 21% (4/19) | 26% (5/19) | -5 pts |
| openai/gpt-6.1-terra | consumer | 95% (19/20) | 95% (19/20) | +0 pts |
| deepseek/deepseek-v4.1-flash-1017 | gov | 16% (3/19) | 5% (1/19) | +11 pts |
| deepseek/deepseek-v4.1-flash-1017 | consumer | 100% (20/20) | 90% (18/20) | +10 pts |
| qwen/qwen4-max | gov | 26% (5/19) | 26% (5/19) | +0 pts |
| qwen/qwen4-max | consumer | 95% (19/20) | 95% (19/20) | +0 pts |
| mistralai/mistral-large-4-0 | gov | 16% (3/19) | 11% (2/19) | +5 pts |
| mistralai/mistral-large-4-0 | consumer | 100% (20/20) | 95% (19/20) | +5 pts |
| moonshotai/kimi-k3.1-pro | gov | 42% (8/19) | 37% (7/19) | +5 pts |
| moonshotai/kimi-k3.1-pro | consumer | 95% (19/20) | 100% (20/20) | -5 pts |

## Cost of the run

- Answering (6 models, 468 answers): $1.327
- Main judge: $0.859
- Second judge: $0.059
- Total: $2.245 (cost as reported by OpenRouter)

## Limits

- 19-20 questions per cell; no confidence intervals; one run at temperature 0.
- Gov reference answers are long; strict accuracy rewards completeness, so absolute levels are low for every model. Compare gaps and ranks, not levels.
- Gov track tests recall of facts as read on 2026-11-17 from u.ae; the facts were not re-verified against live pages in this run.
- Consumer Arabic: for Samsung and Centrepoint items the Arabic follows the retailer's own Arabic page; for Jumbo and Apple items (no Arabic text on the page) the Arabic was drafted by the benchmark author from the English. Consumer models receive the English page text for both languages.
- Gov pair GOV-EN-013 has no Arabic version and is excluded from both languages.
- Retailer help pages are used only as source text for questions; these results say nothing about any company's products or service.
