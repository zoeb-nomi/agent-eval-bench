#!/usr/bin/env python3
"""Reads results/raw + results/judgements, writes results/arabic_gap.md and results/human_label_sheet.csv."""
import json, pathlib, csv, collections, random
ROOT = pathlib.Path(__file__).resolve().parent.parent; R = ROOT / "results"
meta = json.loads((R / "run_meta.json").read_text()); meta = meta.get("earlier_run", meta)  # the scaled run moved the small run here
def jl(j): return [json.loads(l) for l in (R / "judgements" / (j.replace("/", "__") + ".jsonl")).read_text().splitlines()]
J1, J2 = jl(meta["judge"]), jl(meta["judge2"])
def score(v): return {"correct": 1.0, "partial": 0.5}.get(v, 0.0)
def table(J, strict):
    t = collections.defaultdict(lambda: [0.0, 0])
    for r in J:
        t[(r["model"], r["track"], r["lang"])][0] += (1.0 if r["verdict"] == "correct" else 0.0) if strict else score(r["verdict"])
        t[(r["model"], r["track"], r["lang"])][1] += 1
    return t
def fmt(t, m, tr):
    e, a = t[(m, tr, "en")], t[(m, tr, "ar")]
    pe, pa = 100 * e[0] / e[1], 100 * a[0] / a[1]
    return f"| {m} | {tr} | {pe:.0f}% ({e[0]:g}/{e[1]}) | {pa:.0f}% ({a[0]:g}/{a[1]}) | {pe-pa:+.0f} pts |"
out = ["# Arabic gap per model\n",
"> **Not for quotation.** No Arabic reader has checked the Arabic questions, reference answers or any judgement yet. No human has labelled any model answer. Treat every number as a draft.\n",
f"Run date {meta['date']}. Models via OpenRouter, temperature 0. Judge: `{meta['judge']}` (live model). Cross-check judge: `{meta['judge2']}`.",
"Gap = English accuracy minus Arabic accuracy, in percentage points, on the same paired questions (positive = worse in Arabic). Denominator = paired questions (answers judged).\n",
"Tracks: **gov** = 19 UAE government-service questions, closed-book (no page given); **consumer** = 20 returns/delivery/refund questions, answered from the supplied public help-page text (reading in the question's language, so it measures Arabic comprehension and writing, not memory). With 19-20 items per cell one question is about 5 points: gaps under about 10 points are noise.\n"]
for name, strict in (("Strict accuracy (only `correct` counts)", True), ("Partial credit (correct = 1, partial = 0.5)", False)):
    out += [f"## {name}, judge `{meta['judge']}`\n", "| model | track | English | Arabic | gap |", "|---|---|---|---|---|"]
    t = table(J1, strict)
    out += [fmt(t, m, tr) for m in meta["models"] for tr in ("gov", "consumer")]; out.append("")
unp = sum(r["verdict"] == "unparsed" for r in J1); unp2 = sum(r["verdict"] == "unparsed" for r in J2)
# judge agreement
idx2 = {(r["id"], r["model"]): r["verdict"] for r in J2}
pairs = [(r["verdict"], idx2[(r["id"], r["model"])], r["lang"]) for r in J1 if (r["id"], r["model"]) in idx2]
def agree(sub): return f"{sum(a == b for a, b, _ in sub)}/{len(sub)} ({100*sum(a == b for a, b, _ in sub)/max(len(sub),1):.0f}%)"
out += ["## Judge agreement\n",
f"- **Against human labels: not measurable yet.** The 15 'labelled' items shipped with this set were labelled `automated (from source text)` and score the reference answers, not model answers. No human-labelled model answers exist. `results/human_label_sheet.csv` lists a sample of answers with the judge's verdict and an empty column for a person (ideally an Arabic reader) to fill; once filled, agreement can be computed against it.",
f"- Live judge vs second live judge (`{meta['judge2']}`), exact verdict match: all {agree(pairs)}; English {agree([p for p in pairs if p[2]=='en'])}; Arabic {agree([p for p in pairs if p[2]=='ar'])}. Two models agreeing is not the same as a human agreeing.",
f"- Unparsed judge replies (counted as incorrect): {unp} of {len(J1)} (main judge), {unp2} of {len(J2)} (second).",
"- The earlier 91% figure came from a synthetic scoring script that called no model; it has been removed.\n"]
t2 = table(J2, True)
out += [f"## Same strict table under the second judge (`{meta['judge2']}`)\n", "| model | track | English | Arabic | gap |", "|---|---|---|---|---|"] + [fmt(t2, m, tr) for m in meta["models"] for tr in ("gov", "consumer")] + [""]
c = meta
out += ["## Cost of the run\n", f"- Answering ({len(meta['models'])} models, {len(J1)} answers): ${c['answer_cost_usd']:.3f}", f"- Main judge: ${c['judge_cost_usd']:.3f}", f"- Second judge: ${c['judge2_cost_usd']:.3f}", f"- Total: ${c['answer_cost_usd']+c['judge_cost_usd']+c['judge2_cost_usd']:.3f} (cost as reported by OpenRouter)\n",
"## Limits\n",
"- 19-20 questions per cell; no confidence intervals; one run at temperature 0.",
"- Gov reference answers are long; strict accuracy rewards completeness, so absolute levels are low for every model. Compare gaps and ranks, not levels.",
"- Gov track tests recall of facts as read on 2026-11-17 from u.ae; the facts were not re-verified against live pages in this run.",
"- Consumer Arabic: for Samsung and Centrepoint items the Arabic follows the retailer's own Arabic page; for Jumbo and Apple items (no Arabic text on the page) the Arabic was drafted by the benchmark author from the English. Consumer models receive the English page text for both languages.",
"- Gov pair GOV-EN-013 has no Arabic version and is excluded from both languages.",
"- Retailer help pages are used only as source text for questions; these results say nothing about any company's products or service.\n"]
(R / "arabic_gap.md").write_text("\n".join(out))
rnd = random.Random(1); recs = []
raw = {}
for f in (R / "raw").glob("*/*.jsonl"):
    for l in f.read_text().splitlines():
        x = json.loads(l); raw[(x["id"], x["model"])] = x
rows = [r for r in J1]; rnd.shuffle(rows)
sel = [r for r in rows if r["lang"] == "ar"][:30] + [r for r in rows if r["lang"] == "en"][:10]
with open(R / "human_label_sheet.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "model", "language", "question", "model_answer", "judge_verdict", "human_verdict(correct/partial/incorrect)", "human_note"])
    for r in sel:
        x = raw[(r["id"], r["model"])]; w.writerow([r["id"], r["model"], r["lang"], x["question"], x["text"], r["verdict"], "", ""])
print("ok")
