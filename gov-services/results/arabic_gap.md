# Arabic gap per model (scaled run, scorer corrected)

> **The Arabic labels have not been checked by an Arabic reader. No number below may be quoted until a named reader signs off.**

> **The first scaled report overstated the consumer-track gap because of a scoring bug (see "What changed"). The numbers below replace it.**

Report built 2026-11-18. 7 models through OpenRouter, temperature 0, every pair in English and in Arabic. Tracks: **gov** = UAE government services, closed book (500 pairs); **consumer** = customer-support questions answered from the supplied official help page (500 pairs). Accuracy is strict (`partial` counts as wrong). Intervals are 95% (Wilson per language; the gap interval comes from paired differences). The denominator is in every cell: answers that are still empty after the rerun are harness errors and are left out of it, never counted wrong.

## What changed

1. **Yes/no scorer.** The old scorer split on whitespace, so the Arabic no followed by the Arabic comma was not seen as a no. The corrected one drops Arabic and English punctuation, lets the first word decide, and a later no-word cannot flip a yes. A hedge ("I am not sure", "لا أعلم") counts as neither.
2. **List items** match after unifying slash and "or"/"أو", and after stripping the Arabic definite article and the one-letter prefixes on both sides.
3. **Empty answers.** 1260 saved answers were empty or cut off by the token limit (mostly closed-book, reasoning models). They were counted wrong before. Now they are harness errors, left out of the denominators and never counted wrong. They were rerun with reasoning off (then 6000 tokens); 42 are still empty or unjudged and left out.
4. Mean accuracy across the seven models, before and after: gov EN: 42.5% before, 45.2% after; gov AR: 38.5% before, 43.2% after; consumer EN: 98.9% before, 99.1% after; consumer AR: 86.5% before, 98.4% after. Mean gap, consumer: +12.4 before, +0.6 after; gov: +4.0 before, +2.0 after (points).

## Government services (closed book)

| model | lang | old accuracy | corrected accuracy | empty answers before / after rerun |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | EN | 33.2% [29.2, 37.4] (166/500) | 31.2% [27.3, 35.4] (156/500) | 0 / 0 |
| anthropic/claude-haiku-5.5 | AR | 29.8% [26.0, 34.0] (149/500) | 27.8% [24.1, 31.9] (139/500) | 0 / 0 |
| openai/gpt-6.1-terra | EN | 65.4% [61.1, 69.4] (327/500) | 65.2% [60.9, 69.2] (326/500) | 0 / 0 |
| openai/gpt-6.1-terra | AR | 60.8% [56.5, 65.0] (304/500) | 61.8% [57.5, 66.0] (309/500) | 0 / 0 |
| deepseek/deepseek-v4.1-flash-1017 | EN | 55.0% [50.6, 59.3] (275/500) | 55.8% [51.4, 60.1] (279/500) | 33 / 0 |
| deepseek/deepseek-v4.1-flash-1017 | AR | 53.2% [48.8, 57.5] (266/500) | 55.2% [50.8, 59.5] (276/500) | 50 / 0 |
| qwen/qwen4-max | EN | 51.8% [47.4, 56.1] (259/500) | 51.2% [46.8, 55.6] (256/500) | 2 / 0 |
| qwen/qwen4-max | AR | 44.0% [39.7, 48.4] (220/500) | 47.0% [42.7, 51.4] (235/500) | 3 / 0 |
| minimax/minimax-m3.1-flash | EN | 28.4% [24.6, 32.5] (142/500) | 34.7% [30.5, 39.0] (166/479) | 131 / 21 |
| minimax/minimax-m3.1-flash | AR | 26.6% [22.9, 30.6] (133/500) | 34.6% [30.5, 39.0] (169/488) | 144 / 12 |
| tencent/hy4-flash | EN | 36.6% [32.5, 40.9] (183/500) | 40.2% [36.0, 44.6] (201/500) | 168 / 0 |
| tencent/hy4-flash | AR | 28.0% [24.2, 32.1] (140/500) | 39.0% [34.8, 43.3] (195/500) | 271 / 0 |
| meta/muse-ember | EN | 27.0% [23.3, 31.1] (135/500) | 38.0% [33.9, 42.4] (189/497) | 222 / 3 |
| meta/muse-ember | AR | 27.0% [23.3, 31.1] (135/500) | 37.0% [32.9, 41.4] (183/494) | 198 / 6 |

Gap, English minus Arabic, points (paired differences, 95% interval):

| model | old gap | corrected gap |
|---|---|---|
| anthropic/claude-haiku-5.5 | +3.4 [+0.3, +6.5] (n 500) | +3.4 [+0.4, +6.4] (n 500) |
| openai/gpt-6.1-terra | +4.6 [+1.3, +7.9] (n 500) | +3.4 [+0.3, +6.5] (n 500) |
| deepseek/deepseek-v4.1-flash-1017 | +1.8 [-2.2, +5.8] (n 500) | +0.6 [-3.2, +4.4] (n 500) |
| qwen/qwen4-max | +7.8 [+4.0, +11.6] (n 500) | +4.2 [+0.8, +7.6] (n 500) |
| minimax/minimax-m3.1-flash | +1.8 [-1.9, +5.5] (n 500) | -0.2 [-4.0, +3.6] (n 469) |
| tencent/hy4-flash | +8.6 [+5.0, +12.2] (n 500) | +1.2 [-2.6, +5.0] (n 500) |
| meta/muse-ember | +0.0 [-3.4, +3.4] (n 500) | +1.4 [-2.0, +4.9] (n 492) |

## Consumer support (answer from the page)

| model | lang | old accuracy | corrected accuracy | empty answers before / after rerun |
|---|---|---|---|---|
| anthropic/claude-haiku-5.5 | EN | 99.0% [97.7, 99.6] (495/500) | 99.0% [97.7, 99.6] (495/500) | 0 / 0 |
| anthropic/claude-haiku-5.5 | AR | 88.8% [85.7, 91.3] (444/500) | 98.4% [96.9, 99.2] (492/500) | 0 / 0 |
| openai/gpt-6.1-terra | EN | 99.4% [98.3, 99.8] (497/500) | 99.6% [98.6, 99.9] (498/500) | 0 / 0 |
| openai/gpt-6.1-terra | AR | 85.8% [82.5, 88.6] (429/500) | 97.4% [95.6, 98.5] (487/500) | 0 / 0 |
| deepseek/deepseek-v4.1-flash-1017 | EN | 98.8% [97.4, 99.4] (494/500) | 98.8% [97.4, 99.4] (494/500) | 0 / 0 |
| deepseek/deepseek-v4.1-flash-1017 | AR | 88.4% [85.3, 90.9] (442/500) | 98.6% [97.1, 99.3] (493/500) | 0 / 0 |
| qwen/qwen4-max | EN | 99.4% [98.3, 99.8] (497/500) | 99.6% [98.6, 99.9] (498/500) | 0 / 0 |
| qwen/qwen4-max | AR | 86.8% [83.6, 89.5] (434/500) | 99.2% [98.0, 99.7] (496/500) | 0 / 0 |
| minimax/minimax-m3.1-flash | EN | 99.0% [97.7, 99.6] (495/500) | 99.0% [97.7, 99.6] (495/500) | 0 / 0 |
| minimax/minimax-m3.1-flash | AR | 88.0% [84.9, 90.6] (440/500) | 97.8% [96.1, 98.8] (489/500) | 0 / 0 |
| tencent/hy4-flash | EN | 98.6% [97.1, 99.3] (493/500) | 99.0% [97.7, 99.6] (495/500) | 1 / 0 |
| tencent/hy4-flash | AR | 82.4% [78.8, 85.5] (412/500) | 98.8% [97.4, 99.4] (494/500) | 23 / 0 |
| meta/muse-ember | EN | 98.2% [96.6, 99.1] (491/500) | 98.4% [96.9, 99.2] (492/500) | 5 / 0 |
| meta/muse-ember | AR | 85.4% [82.0, 88.2] (427/500) | 98.8% [97.4, 99.4] (494/500) | 9 / 0 |

Gap, English minus Arabic, points (paired differences, 95% interval):

| model | old gap | corrected gap |
|---|---|---|
| anthropic/claude-haiku-5.5 | +10.2 [+7.3, +13.1] (n 500) | +0.6 [-0.8, +2.0] (n 500) |
| openai/gpt-6.1-terra | +13.6 [+10.5, +16.7] (n 500) | +2.2 [+0.7, +3.7] (n 500) |
| deepseek/deepseek-v4.1-flash-1017 | +10.4 [+7.4, +13.4] (n 500) | +0.2 [-1.2, +1.6] (n 500) |
| qwen/qwen4-max | +12.6 [+9.5, +15.7] (n 500) | +0.4 [-0.6, +1.4] (n 500) |
| minimax/minimax-m3.1-flash | +11.0 [+8.0, +14.0] (n 500) | +1.2 [-0.4, +2.8] (n 500) |
| tencent/hy4-flash | +16.2 [+12.7, +19.7] (n 500) | +0.2 [-1.1, +1.5] (n 500) |
| meta/muse-ember | +12.8 [+9.6, +16.0] (n 500) | -0.4 [-1.8, +1.0] (n 500) |

## How answers were scored

- By code (number, fee, duration, document list or yes/no): 9211 of 13958 scored runs.
- By the judge (`deepseek/deepseek-v4.1-flash-1017`): 4747 runs. Harness errors left out: 42.
- Judge vs second judge (`anthropic/claude-sonnet-5.5`) on a random sample: 303/320 identical verdicts (95%).
- Code scorer vs the cheap judge, random sample of code-scored answers (corrected scorer): EN 303/325 agree (93%); AR 308/318 agree (97%).
- Judge vs the human-labelled subset: Not measured: no human has labelled any model answer. `results/human_label_sheet.csv` holds the sample for an Arabic reader to fill; save the filled copy as `results/human_labels.csv` and rerun this report.

## For a human check

**English and Arabic gold answers that disagree** (92 pairs by the rule: yes/no differs, or the numbers in the gold sentences differ; the issue counted 13, this rule is broader). A gold answer that is wrong in one language makes the gap look bigger or smaller for that pair. Full list with reasons: `results/human_check_pairs.csv`.

- GOV-0119: yes/no differs: English no, Arabic yes
- CONSUMER-0140: yes/no differs: English no, Arabic yes

**Consumer-track items (pair + language) that every model, or all but one, gets wrong:** 3: CONSUMER-0043 AR (7/7 wrong), CONSUMER-0076 AR (7/7 wrong), CONSUMER-0389 EN (6/7 wrong). On the closed-book track 94 pairs are failed by every model (expected for obscure facts); they are in `results/human_check_pairs.csv`. All are listed for a human to check the gold answer and the question, none is dropped.

## Totals

- Scored runs: 13958; answer cost incl. reruns $7.23; judging cost $1.44 (OpenRouter-reported).

## Models that could not be run

Searched the OpenRouter model list on the run date; none of these Arabic-first models is offered there: Jais (Inception / G42); Falcon Arabic and Falcon-H1 Arabic (TII); ALLaM (HUMAIN / SDAIA); Fanar (QCRI); SILMA; Cohere Aya.

## Limits

- Arabic questions and gold answers were written by a model from the Arabic page; no Arabic reader has checked them.
- Gold answers are condensed by a model from the page; a few may be incomplete. Pages were read on the date in each item and change over time.
- One run at temperature 0. The code yes/no scorer treats a refusal as neither yes nor no; an answer like "لا بأس" (no problem) would be read as no.
- Consumer-track help pages are used only as source text; retailer names are removed from the questions. These results say nothing about any company's product or service.
