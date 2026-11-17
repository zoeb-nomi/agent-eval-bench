> **The Arabic labels have not yet been checked by an Arabic reader. No number here may be quoted until they are.**

# gov-services: Arabic vs English gap

Two tracks, each item in English and Arabic with source URL and date read: UAE government services (closed-book) and consumer support (returns, delivery, refunds; from public help pages). Six models run through OpenRouter; every raw answer is in `results/raw/`. Tables, judge agreement and run cost: `results/arabic_gap.md`. Rerun: `python scripts/run_bench.py` then `python scripts/report_gap.py` (needs `OPENROUTER_API_KEY` in the environment). `scripts/fixtures/` holds a small smoke set (`--smoke`).

The judge is a live model. Agreement with a human is not yet measured: `results/human_label_sheet.csv` awaits a human label. Nothing here makes a claim about any company's product.
