# PRD: gov-services Arabic gap benchmark (scaled)

One page. Status: built and run 17 Nov 2026; Arabic labels not yet read by an Arabic reader.

## 1. Question this answers
Do general-purpose models answer the same practical question as well in Arabic as in English? Two tracks, 500 pairs each: UAE government services (closed book) and consumer support (answer from an official help page).

## 2. Users
1. AI PM campaign: citable evidence for UAE AI teams (ai71, Brain Co., Emirates, consumer companies).
2. Eval owner: reruns the build and the run from the page list.
3. Arabic reader (to be named): labels the Arabic subset and signs off before any number is quoted.

## 3. Method
- Pairs are built from public pages that exist officially in both languages. The English question is written from the English page; the Arabic question is written from the Arabic page about the same fact (not a translation). Each item has both source URLs, the date read and a short gold answer.
- Items whose answer is a number, fee, duration, document list or yes/no are `exact` and scored by code; the rest are scored by a cheap judge (deepseek-v4.1-flash). Sonnet re-judges a random 300 answers to measure agreement with the cheap judge.
- Seven models through OpenRouter, every item in both languages, temperature 0. Accuracy is strict, with a 95% Wilson interval and the denominator; the gap is English minus Arabic on the same pairs.
- Duplicate and near-duplicate check on both languages before selection. Rebuild: `scripts/build_sets.py`; run: `scripts/run_scale.py`; report: `scripts/report_scale.py`. Cached and resumable.

## 4. Decisions and trade-offs
- Money: pilot projected 51.89 USD for ten models; Zoeb approved up to 10 USD with three models dropped and cheaper judging. Final cost is in `results/arabic_gap.md`.
- Eight models were asked for; seven were run under that ceiling. Arabic-first models (Jais, Falcon Arabic, ALLaM, Fanar) are not on OpenRouter; a separate task plans a free local run.
- Size: about plus or minus 4 points per cell at n=500; the exact share makes scoring cheap and objective.
- Limits: model-written Arabic questions and gold answers; static snapshot of pages; one run per model; no claim about any company's product (help pages are source text only).

## 5. Open
Name an Arabic reader; fill `results/human_label_sheet.csv`; rerun the report to get agreement with human labels. Until then, no number is quotable.
