#!/usr/bin/env python3
"""results/arabic_gap.md + results/arabic_gap.csv + results/human_label_sheet.csv from the cached raw answers and judgements.
Score of one answer: exact item -> code (common.score_exact); otherwise the judge (correct = 1, partial and incorrect = 0, strict).
95% interval: Wilson on the share correct. Gap = English minus Arabic on the same pairs, interval from the paired differences (normal approx.)."""
import collections, csv, json, math, pathlib, sys, argparse, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import score_exact, wilson
from run_scale import pairs, read_cache, raw_file, judge_file, MODELS, JUDGE, JUDGE2
ROOT = pathlib.Path(__file__).resolve().parent.parent; RES = ROOT / "results"
UNAVAILABLE = ["Jais (Inception / G42)", "Falcon Arabic and Falcon-H1 Arabic (TII)", "ALLaM (HUMAIN / SDAIA)", "Fanar (QCRI)", "SILMA", "Cohere Aya"]

def build(ps, models, judge, judge_cache=None):
    byid = {p["pair_id"]: p for p in ps}; J = {(r["pair_id"], r["lang"], r["model"]): r["verdict"] for r in map(json.loads, judge_file(judge).read_text().splitlines())} if judge_file(judge).exists() else {}
    rows = []
    for m in models:
        for (pid, lang), r in read_cache(raw_file(m)).items():
            p = byid.get(pid)
            if not p: continue
            if p["exact"]: ok, how = score_exact(p[lang]["exact"], r["text"], lang), "code"
            else:
                v = J.get((pid, lang, m)); 
                if v is None: continue
                ok, how = v == "correct", "judge"
            rows.append({"pair_id": pid, "model": m, "track": p["track"], "lang": lang, "ok": bool(ok), "how": how, "cost": r["cost"], "latency_s": r["latency_s"]})
    return rows, J

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--questions", default=str(ROOT / "questions")); a = ap.parse_args()
    ps = pairs(pathlib.Path(a.questions)); meta = json.loads((RES / "pilot_projection.json").read_text()) if (RES / "pilot_projection.json").exists() else {}
    models = [m for m in MODELS if raw_file(m).exists()]
    rows, J = build(ps, models, JUDGE)
    cell = collections.defaultdict(list); pairmap = {}
    for r in rows: cell[(r["model"], r["track"], r["lang"])].append(r["ok"]); pairmap[(r["model"], r["track"], r["pair_id"], r["lang"])] = r["ok"]
    csv_rows = []; lines = []
    for m in models:
        for t in ("gov", "consumer"):
            e, ar_ = cell[(m, t, "en")], cell[(m, t, "ar")]
            if not e or not ar_: continue
            ids = [pid for (mm, tt, pid, l) in pairmap if mm == m and tt == t and l == "en" and (m, t, pid, "ar") in pairmap]
            d = [pairmap[(m, t, i, "en")] - pairmap[(m, t, i, "ar")] for i in ids]; nd = len(d); mean = sum(d) / nd; sd = math.sqrt(sum((x - mean) ** 2 for x in d) / max(nd - 1, 1)); h = 1.96 * sd / math.sqrt(nd)
            for lang, c in (("en", e), ("ar", ar_)):
                lo, hi = wilson(sum(c), len(c)); csv_rows.append({"model": m, "track": t, "lang": lang, "n": len(c), "correct": sum(c), "accuracy": round(sum(c) / len(c), 4), "ci95_low": round(lo, 4), "ci95_high": round(hi, 4)})
            csv_rows.append({"model": m, "track": t, "lang": "gap_en_minus_ar", "n": nd, "correct": "", "accuracy": round(mean, 4), "ci95_low": round(mean - h, 4), "ci95_high": round(mean + h, 4)})
    with open(RES / "arabic_gap.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "track", "lang", "n", "correct", "accuracy", "ci95_low", "ci95_high"]); w.writeheader(); w.writerows(csv_rows)
    pct = lambda x: f"{100 * x:.1f}"
    def tbl(t):
        out = ["| model | English | Arabic | gap (EN minus AR, points) | n pairs |", "|---|---|---|---|---|"]
        for m in models:
            g = {r["lang"]: r for r in csv_rows if r["model"] == m and r["track"] == t}
            if "en" not in g or "ar" not in g: continue
            f = lambda r: f"{pct(r['accuracy'])}% [{pct(r['ci95_low'])}, {pct(r['ci95_high'])}] ({r['correct']}/{r['n']})"; gp = g["gap_en_minus_ar"]
            out.append(f"| {m} | {f(g['en'])} | {f(g['ar'])} | {100 * gp['accuracy']:+.1f} [{100 * gp['ci95_low']:+.1f}, {100 * gp['ci95_high']:+.1f}] | {gp['n']} |")
        return out
    byhow = collections.Counter(r["how"] for r in rows); tot_runs = len(rows)
    ans_cost = sum(r["cost"] for r in rows); jcost = sum(json.loads(l)["cost"] for f in (judge_file(JUDGE), judge_file(JUDGE2)) if f.exists() for l in f.read_text().splitlines())
    # agreement
    j1 = J; j2 = {(r["pair_id"], r["lang"], r["model"]): r["verdict"] for r in map(json.loads, judge_file(JUDGE2).read_text().splitlines())} if judge_file(JUDGE2).exists() else {}
    both = [k for k in j2 if k in j1]; agree = sum(j1[k] == j2[k] for k in both)
    byid = {p["pair_id"]: p for p in ps}; rawc = {m: read_cache(raw_file(m)) for m in models}
    ex_chk = [k for k in j1 if byid[k[0]]["exact"] and k[2] in rawc]; ex_agree = sum(score_exact(byid[k[0]][k[1]]["exact"], rawc[k[2]][(k[0], k[1])]["text"], k[1]) == (j1[k] == "correct") for k in ex_chk)
    human = RES / "human_labels.csv"; hl = "Not measured: no human has labelled any model answer. `results/human_label_sheet.csv` holds the sample for an Arabic reader to fill; save the filled copy as `results/human_labels.csv` and rerun this report."
    if human.exists():
        hr = list(csv.DictReader(human.open())); hk = [(r["pair_id"], r["lang"], r["model"], r["human_verdict"]) for r in hr if r.get("human_verdict")]
        if hk:
            ha = sum(J.get((p, l, m), "") == hv or (byid[p]["exact"] and (score_exact(byid[p][l]["exact"], rawc[m][(p, l)]["text"], l) == (hv == "correct"))) for p, l, m, hv in hk)
            hl = f"{ha}/{len(hk)} ({100 * ha / len(hk):.0f}%) exact match with the human-labelled subset."
    n_pairs = collections.Counter(p["track"] for p in ps); ar_basis = "Arabic questions and gold answers were written by a model from the Arabic page; no Arabic reader has checked them."
    md = ["# Arabic gap per model (scaled run)\n",
          "> **The Arabic labels have not been checked by an Arabic reader. No number below may be quoted until a named reader signs off.**\n",
          f"Report built {time.strftime('%Y-%m-%d')}. {len(models)} models through OpenRouter, temperature 0, every pair in English and in Arabic. Tracks: **gov** = UAE government services, closed book ({n_pairs['gov']} pairs); **consumer** = customer-support questions answered from the supplied official help page, in the question's language ({n_pairs['consumer']} pairs). Accuracy is strict (a verdict of `partial` counts as wrong). Intervals are 95% (Wilson for each language; the gap interval comes from the paired differences). The denominator is shown in every cell.\n",
          "## Government services (closed book)\n"] + tbl("gov") + ["", "## Consumer support (answer from the page)\n"] + tbl("consumer") + [
          "", "## How answers were scored\n", f"- By code (exact items: a number, fee, duration, document list or yes/no): {byhow['code']} of {tot_runs} runs ({100 * byhow['code'] / max(tot_runs, 1):.0f}%).",
          f"- By the judge (`{JUDGE}`): {byhow['judge']} runs ({100 * byhow['judge'] / max(tot_runs, 1):.0f}%).",
          f"- Judge vs second judge (`{JUDGE2}`) on a random sample: {agree}/{len(both)} identical verdicts" + (f" ({100 * agree / len(both):.0f}%)." if both else "."),
          f"- Code scorer vs judge on a sample of exact items: {ex_agree}/{len(ex_chk)} agree" + (f" ({100 * ex_agree / len(ex_chk):.0f}%)." if ex_chk else "."),
          f"- Judge vs the human-labelled subset: {hl}", "",
          "## Totals\n", f"- Scored runs: {tot_runs} (answers; each model x pair x language).", f"- Answer cost: ${ans_cost:.2f}; judging cost: ${jcost:.2f}; total ${ans_cost + jcost:.2f} (as reported by OpenRouter; question generation cost is in `questions/dedupe_report.json`).",
          f"- Median latency per answer: {sorted(r['latency_s'] for r in rows)[len(rows) // 2] if rows else 0:.1f} s.", "",
          "## Models that could not be run\n", "Searched the OpenRouter model list on the run date; none of these Arabic-first models is offered there: " + "; ".join(UNAVAILABLE) + ". The run covers the general models listed above only; an Arabic-first comparison needs another host.", "",
          "## Limits\n", f"- {ar_basis}", "- Gold answers are condensed by a model from the page; a few may be incomplete. Pages were read on the date in each item and change over time.",
          "- One run at temperature 0; no repeated sampling. Reasoning models were run with low reasoning effort where the host supports it.",
          "- Consumer-track help pages are used only as source text. Retailer names are removed from the questions. These results say nothing about any company's product or service.", ""]
    # run_meta.json describes this (scaled) run; the earlier small run's record is kept under "earlier_run" for scripts/report_gap.py
    mp = RES / "run_meta.json"; old = json.loads(mp.read_text()) if mp.exists() else {}
    earlier = old.get("earlier_run", old if old and "run" not in old else None)
    jc = {j: round(sum(json.loads(l)["cost"] for l in judge_file(j).read_text().splitlines()), 4) if judge_file(j).exists() else 0 for j in (JUDGE, JUDGE2)}
    meta_out = {"run": "scaled", "date": time.strftime("%Y-%m-%d"), "models": models, "unavailable_on_openrouter": UNAVAILABLE,
                "pairs": dict(n_pairs), "languages": ["en", "ar"], "scored_runs": tot_runs, "scored_by_code": byhow["code"], "scored_by_judge": byhow["judge"],
                "judge": JUDGE, "judge2_sample": JUDGE2, "judge2_sample_size": len(both), "judge2_agreement": agree,
                "answer_cost_usd": round(ans_cost, 4), "answer_cost_usd_by_model": {m: round(sum(r["cost"] for r in rows if r["model"] == m), 4) for m in models},
                "judge_cost_usd": jc[JUDGE], "judge2_cost_usd": jc[JUDGE2], "total_cost_usd": round(ans_cost + jcost, 4), "human_labelled_subset": "not yet labelled" if not human.exists() else "see arabic_gap.md"}
    if earlier: meta_out["earlier_run"] = earlier
    mp.write_text(json.dumps(meta_out, indent=1, ensure_ascii=False) + "\n")
    (RES / "arabic_gap.md").write_text("\n".join(md))
    import random
    rnd = random.Random(3); cand = [r for r in rows if r["how"] == "judge" or True]; rnd.shuffle(cand)
    sel = [r for r in cand if r["lang"] == "ar"][:60] + [r for r in cand if r["lang"] == "en"][:40]
    with open(RES / "human_label_sheet.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["pair_id", "lang", "model", "question", "gold_answer", "model_answer", "scored_by", "auto_verdict", "human_verdict(correct/partial/incorrect)", "human_note"])
        for r in sel:
            p = byid[r["pair_id"]]; a = rawc[r["model"]][(r["pair_id"], r["lang"])]["text"]
            w.writerow([r["pair_id"], r["lang"], r["model"], p[r["lang"]]["question"], p[r["lang"]]["gold"], a, r["how"], "correct" if r["ok"] else "not correct", "", ""])
    print("\n".join(md[:30]))

if __name__ == "__main__": main()
