# Arabic gap per model (scaled run)

> **The Arabic labels have not been checked by an Arabic reader. No number below may be quoted until a named reader signs off.**

Report built 2026-11-17. 7 models through OpenRouter, temperature 0, every pair in English and in Arabic. Tracks: **gov** = UAE government services, closed book (500 pairs); **consumer** = customer-support questions answered from the supplied official help page, in the question's language (500 pairs). Accuracy is strict (a verdict of `partial` counts as wrong). Intervals are 95% (Wilson for each language; the gap interval comes from the paired differences). The denominator is shown in every cell.

## Government services (closed book)

| model | English | Arabic | gap (EN minus AR, points) | n pairs |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | 33.2% [29.2, 37.4] (166/500) | 29.8% [26.0, 34.0] (149/500) | +3.4 [+0.3, +6.5] | 500 |
| openai/gpt-6.1-terra | 65.4% [61.1, 69.4] (327/500) | 60.8% [56.5, 65.0] (304/500) | +4.6 [+1.3, +7.9] | 500 |
| deepseek/deepseek-v4.1-flash-1017 | 55.0% [50.6, 59.3] (275/500) | 53.2% [48.8, 57.5] (266/500) | +1.8 [-2.2, +5.8] | 500 |
| qwen/qwen4-max | 51.8% [47.4, 56.1] (259/500) | 44.0% [39.7, 48.4] (220/500) | +7.8 [+4.0, +11.6] | 500 |
| minimax/minimax-m3.1-flash | 28.4% [24.6, 32.5] (142/500) | 26.6% [22.9, 30.6] (133/500) | +1.8 [-1.9, +5.5] | 500 |
| tencent/hy4-flash | 36.6% [32.5, 40.9] (183/500) | 28.0% [24.2, 32.1] (140/500) | +8.6 [+5.0, +12.2] | 500 |
| meta/muse-ember | 27.0% [23.3, 31.1] (135/500) | 27.0% [23.3, 31.1] (135/500) | +0.0 [-3.4, +3.4] | 500 |

## Consumer support (answer from the page)

| model | English | Arabic | gap (EN minus AR, points) | n pairs |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | 99.0% [97.7, 99.6] (495/500) | 88.8% [85.7, 91.3] (444/500) | +10.2 [+7.3, +13.1] | 500 |
| openai/gpt-6.1-terra | 99.4% [98.2, 99.8] (497/500) | 85.8% [82.5, 88.6] (429/500) | +13.6 [+10.5, +16.7] | 500 |
| deepseek/deepseek-v4.1-flash-1017 | 98.8% [97.4, 99.5] (494/500) | 88.4% [85.3, 90.9] (442/500) | +10.4 [+7.4, +13.4] | 500 |
| qwen/qwen4-max | 99.4% [98.2, 99.8] (497/500) | 86.8% [83.5, 89.5] (434/500) | +12.6 [+9.5, +15.7] | 500 |
| minimax/minimax-m3.1-flash | 99.0% [97.7, 99.6] (495/500) | 88.0% [84.9, 90.6] (440/500) | +11.0 [+8.0, +14.0] | 500 |
| tencent/hy4-flash | 98.6% [97.1, 99.3] (493/500) | 82.4% [78.8, 85.5] (412/500) | +16.2 [+12.7, +19.7] | 500 |
| meta/muse-ember | 98.2% [96.6, 99.1] (491/500) | 85.4% [82.0, 88.2] (427/500) | +12.8 [+9.6, +16.0] | 500 |

## How answers were scored

- By code (exact items: a number, fee, duration, document list or yes/no): 9240 of 14000 runs (66%).
- By the judge (`deepseek/deepseek-v4.1-flash-1017`): 4760 runs (34%).
- Judge vs second judge (`anthropic/claude-sonnet-5.5`) on a random sample: 303/320 identical verdicts (95%).
- Code scorer vs judge on a sample of exact items: 0/0 agree.
- Judge vs the human-labelled subset: Not measured: no human has labelled any model answer. `results/human_label_sheet.csv` holds the sample for an Arabic reader to fill; save the filled copy as `results/human_labels.csv` and rerun this report.

## Totals

- Scored runs: 14000 (answers; each model x pair x language).
- Answer cost: $6.38; judging cost: $1.34; total $7.71 (as reported by OpenRouter; question generation cost is in `questions/dedupe_report.json`).
- Median latency per answer: 2.7 s.

## Models that could not be run

Searched the OpenRouter model list on the run date; none of these Arabic-first models is offered there: Jais (Inception / G42); Falcon Arabic and Falcon-H1 Arabic (TII); ALLaM (HUMAIN / SDAIA); Fanar (QCRI); SILMA; Cohere Aya. The run covers the general models listed above only; an Arabic-first comparison needs another host.

## Limits

- Arabic questions and gold answers were written by a model from the Arabic page; no Arabic reader has checked them.
- Gold answers are condensed by a model from the page; a few may be incomplete. Pages were read on the date in each item and change over time.
- One run at temperature 0; no repeated sampling. Reasoning models were run with low reasoning effort where the host supports it.
- Consumer-track help pages are used only as source text. Retailer names are removed from the questions. These results say nothing about any company's product or service.
