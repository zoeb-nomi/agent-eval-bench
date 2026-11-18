#!/usr/bin/env python3
"""results/arabic_gap.md + results/arabic_gap.csv + results/human_label_sheet.csv from the cached raw answers and judgements.
Score of one answer: exact item -> code (common.score_exact); otherwise the judge (correct = 1, partial and incorrect = 0, strict).
95% interval: Wilson on the share correct. Gap = English minus Arabic on the same pairs, interval from the paired differences (normal approx.)."""
import collections, csv, json, math, pathlib, re, sys, argparse, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import score_exact, score_exact_legacy, wilson, norm
from rescore import effective_answers
from run_scale import pairs, read_cache, raw_file, judge_file, MODELS, JUDGE, JUDGE2
ROOT = pathlib.Path(__file__).resolve().parent.parent; RES = ROOT / "results"
UNAVAILABLE = ["Jais (Inception / G42)", "Falcon Arabic and Falcon-H1 Arabic (TII)", "ALLaM (HUMAIN / SDAIA)", "Fanar (QCRI)", "SILMA", "Cohere Aya"]

def verdicts(f): return {(r["pair_id"], r["lang"], r["model"]): r["verdict"] for r in map(json.loads, f.read_text().splitlines())} if f.exists() else {}

def score_all(ps, models):
    """One row per saved answer: old (legacy scorer, saved text, empties counted wrong) and new (corrected scorer, rerun text, harness errors left out)."""
    byid = {p["pair_id"]: p for p in ps}; J = verdicts(judge_file(JUDGE)); JR = verdicts(judge_file("rerun__" + JUDGE.replace("/", "__")))
    rows = []
    for a in effective_answers(models):
        p = byid.get(a["pair_id"])
        if not p: continue
        pid, lang, m = a["pair_id"], a["lang"], a["model"]; new = old = None
        if p["exact"]:
            old = score_exact_legacy(p[lang]["exact"], a["orig_text"], lang)
            new = None if a["harness_error"] else score_exact(p[lang]["exact"], a["text"], lang)
        else:
            v = J.get((pid, lang, m)); old = None if v is None else v == "correct"
            vn = JR.get((pid, lang, m)) if a["reran"] else v
            new = None if (a["harness_error"] or vn is None) else vn == "correct"
        if old is None and new is None and not a["harness_error"]: continue
        rows.append({"pair_id": pid, "model": m, "track": a["track"], "lang": lang, "old": old, "ok": new, "how": "code" if p["exact"] else "judge",
                     "orig_bad": a["orig_bad"], "harness_error": a["harness_error"], "cost": a["cost"], "latency_s": a["latency_s"]})
    return rows, J

def cell_stats(rows, models, key):
    """per (model, track, lang): n, correct, accuracy, Wilson; per (model, track): paired gap. key = 'old' or 'ok'."""
    cell = collections.defaultdict(dict)
    for r in rows:
        if r[key] is not None: cell[(r["model"], r["track"], r["lang"])][r["pair_id"]] = bool(r[key])
    out = {}
    for m in models:
        for t in ("gov", "consumer"):
            e, a_ = cell[(m, t, "en")], cell[(m, t, "ar")]
            for lang, c in (("en", e), ("ar", a_)):
                n = len(c); k = sum(c.values()); lo, hi = wilson(k, n)
                out[(m, t, lang)] = {"n": n, "correct": k, "accuracy": k / n if n else 0, "lo": lo, "hi": hi}
            ids = sorted(set(e) & set(a_)); d = [int(e[i]) - int(a_[i]) for i in ids]; nd = len(d)
            if nd:
                mean = sum(d) / nd; sd = math.sqrt(sum((x - mean) ** 2 for x in d) / max(nd - 1, 1)); h = 1.96 * sd / math.sqrt(nd)
                out[(m, t, "gap")] = {"n": nd, "accuracy": mean, "lo": mean - h, "hi": mean + h}
    return out

def human_check_lists(ps, rows, models):
    """(1) pairs whose English and Arabic gold answers disagree; (2) pairs every model fails (all scored answers wrong, both languages)."""
    dg = lambda t: sorted(re.findall(r"\d+", norm(t).replace(",", "")))
    cand = []
    for p in ps:
        why = []
        if p["exact"] and p["en"]["exact"]["type"] == "yesno" and norm(str(p["en"]["exact"]["values"][0])) != norm(str(p["ar"]["exact"]["values"][0])) and p["ar"]["exact"]["values"][0] in ("yes", "no"):
            why.append(f"yes/no differs: English {p['en']['exact']['values'][0]}, Arabic {p['ar']['exact']['values'][0]}")
        if dg(p["en"]["gold"]) != dg(p["ar"]["gold"]): why.append(f"numbers in the gold sentence differ: {dg(p['en']['gold'])} vs {dg(p['ar']['gold'])}")
        if why: cand.append((p, why))
    bypair = collections.defaultdict(list)
    for r in rows:
        if r["ok"] is not None: bypair[(r["pair_id"], r["lang"])].append(r["ok"])
    cf_ = [(pid, lang, sum(not x for x in v), len(v)) for (pid, lang), v in sorted(bypair.items()) if pid.startswith("CONSUMER") and len(v) >= len(models) - 1 and sum(not x for x in v) >= len(v) - 1]
    allfail = [p for p in ps if all(len(bypair[(p["pair_id"], l)]) >= len(models) - 2 and not any(bypair[(p["pair_id"], l)]) for l in ("en", "ar"))]
    return cand, allfail, cf_

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--questions", default=str(ROOT / "questions")); a = ap.parse_args()
    ps = pairs(pathlib.Path(a.questions)); models = [m for m in MODELS if raw_file(m).exists()]
    rows, J = score_all(ps, models); old, new = cell_stats(rows, models, "old"), cell_stats(rows, models, "ok")
    empt_b, empt_a = collections.Counter(), collections.Counter()
    for r in rows: empt_b[(r["model"], r["track"], r["lang"])] += r["orig_bad"]; empt_a[(r["model"], r["track"], r["lang"])] += r["harness_error"]
    csv_rows = []
    for m in models:
        for t in ("gov", "consumer"):
            for lang in ("en", "ar", "gap"):
                o, n_ = old.get((m, t, lang)), new.get((m, t, lang))
                if not o or not n_: continue
                csv_rows.append({"model": m, "track": t, "lang": "gap_en_minus_ar" if lang == "gap" else lang,
                                 "old_n": o["n"], "old_correct": o.get("correct", ""), "old_accuracy": round(o["accuracy"], 4), "old_ci95_low": round(o["lo"], 4), "old_ci95_high": round(o["hi"], 4),
                                 "n": n_["n"], "correct": n_.get("correct", ""), "accuracy": round(n_["accuracy"], 4), "ci95_low": round(n_["lo"], 4), "ci95_high": round(n_["hi"], 4),
                                 "empty_before": "" if lang == "gap" else empt_b[(m, t, lang)], "empty_after": "" if lang == "gap" else empt_a[(m, t, lang)]})
    with open(RES / "arabic_gap.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(csv_rows[0])); w.writeheader(); w.writerows(csv_rows)
    pct = lambda x: f"{100 * x:.1f}"
    f = lambda r: f"{pct(r['accuracy'])}% [{pct(r['lo'])}, {pct(r['hi'])}] ({r['correct']}/{r['n']})"
    fg = lambda r: f"{100 * r['accuracy']:+.1f} [{100 * r['lo']:+.1f}, {100 * r['hi']:+.1f}] (n {r['n']})"
    def tbl(t):
        out = ["| model | lang | old accuracy | corrected accuracy | empty answers before / after rerun |", "|---|---|---|---|---|"]
        for m in models:
            for lang in ("en", "ar"):
                if (m, t, lang) in new: out.append(f"| {m} | {lang.upper()} | {f(old[(m, t, lang)])} | {f(new[(m, t, lang)])} | {empt_b[(m, t, lang)]} / {empt_a[(m, t, lang)]} |")
        out += ["", "Gap, English minus Arabic, points (paired differences, 95% interval):", "", "| model | old gap | corrected gap |", "|---|---|---|"]
        for m in models:
            if (m, t, "gap") in new: out.append(f"| {m} | {fg(old[(m, t, 'gap')])} | {fg(new[(m, t, 'gap')])} |")
        return out
    byhow = collections.Counter(r["how"] for r in rows if r["ok"] is not None); tot_runs = sum(byhow.values()); n_he = sum(r["harness_error"] for r in rows)
    ans_cost = sum(r["cost"] for r in rows); jcost = sum(json.loads(l)["cost"] for ff in judge_file(JUDGE).parent.glob("*.jsonl") for l in ff.read_text().splitlines())
    j1 = J; j2 = verdicts(judge_file(JUDGE2)); both = [k for k in j2 if k in j1]; agree = sum(j1[k] == j2[k] for k in both)
    byid = {p["pair_id"]: p for p in ps}; ans_by = {(x["pair_id"], x["lang"], x["model"]): x for x in effective_answers(models)}
    cc = verdicts(judge_file("code_check__" + JUDGE.replace("/", "__"))); cc_lang = {}
    for lang in ("en", "ar"):
        ks = [k for k in cc if k[1] == lang and cc[k] in ("correct", "partial", "incorrect") and not ans_by[k]["harness_error"]]
        ag = sum(score_exact(byid[k[0]][lang]["exact"], ans_by[k]["text"], lang) == (cc[k] == "correct") for k in ks); cc_lang[lang] = (ag, len(ks))
    cc_line = ("- Code scorer vs the cheap judge, random sample of code-scored answers (corrected scorer): " + "; ".join(f"{l.upper()} {a_}/{n_} agree ({100 * a_ / n_:.0f}%)" for l, (a_, n_) in cc_lang.items() if n_) + ".") if any(n_ for _, n_ in cc_lang.values()) else "- Code scorer vs the cheap judge: **not yet run** (needs the judge calls of `scripts/check_scorer.py`)."
    human = RES / "human_labels.csv"; hl = "Not measured: no human has labelled any model answer. `results/human_label_sheet.csv` holds the sample for an Arabic reader to fill; save the filled copy as `results/human_labels.csv` and rerun this report."
    cand, allfail, cf_ = human_check_lists(ps, rows, models)
    n_pairs = collections.Counter(p["track"] for p in ps)
    chg = []
    for t in ("gov", "consumer"):
        for lang in ("en", "ar"):
            ov = [100 * old[(m, t, lang)]["accuracy"] for m in models]; nv = [100 * new[(m, t, lang)]["accuracy"] for m in models if (m, t, lang) in new]
            chg.append(f"{t} {lang.upper()}: {sum(ov) / len(ov):.1f}% before, {sum(nv) / len(nv):.1f}% after")
    gm = lambda d, t: sum(100 * d[(m, t, "gap")]["accuracy"] for m in models) / len(models)
    md = ["# Arabic gap per model (scaled run, scorer corrected)\n",
          "> **The Arabic labels have not been checked by an Arabic reader. No number below may be quoted until a named reader signs off.**\n",
          "> **The first scaled report overstated the consumer-track gap because of a scoring bug (see \"What changed\"). The numbers below replace it.**\n",
          f"Report built {time.strftime('%Y-%m-%d')}. {len(models)} models through OpenRouter, temperature 0, every pair in English and in Arabic. Tracks: **gov** = UAE government services, closed book ({n_pairs['gov']} pairs); **consumer** = customer-support questions answered from the supplied official help page ({n_pairs['consumer']} pairs). Accuracy is strict (`partial` counts as wrong). Intervals are 95% (Wilson per language; the gap interval comes from paired differences). The denominator is in every cell: answers that are still empty after the rerun are harness errors and are left out of it, never counted wrong.\n",
          "## What changed\n",
          "1. **Yes/no scorer.** The old scorer split on whitespace, so the Arabic no followed by the Arabic comma was not seen as a no. The corrected one drops Arabic and English punctuation, lets the first word decide, and a later no-word cannot flip a yes. A hedge (\"I am not sure\", \"لا أعلم\") counts as neither.",
          "2. **List items** match after unifying slash and \"or\"/\"أو\", and after stripping the Arabic definite article and the one-letter prefixes on both sides.",
          f"3. **Empty answers.** {sum(empt_b.values())} saved answers were empty or cut off by the token limit (mostly closed-book, reasoning models). They were counted wrong before. Now they are harness errors, left out of the denominators and never counted wrong. " + (f"**The rerun (reasoning off, then 6000 tokens) has not run yet**, so all {n_he} are still left out and the closed-book cells are on fewer answers than 500." if n_he == sum(empt_b.values()) else f"They were rerun with reasoning off (then 6000 tokens); {n_he} are still empty or unjudged and left out."),
          "4. Mean accuracy across the seven models, before and after: " + "; ".join(chg) + f". Mean gap, consumer: {gm(old, 'consumer'):+.1f} before, {gm(new, 'consumer'):+.1f} after; gov: {gm(old, 'gov'):+.1f} before, {gm(new, 'gov'):+.1f} after (points).", "",
          "## Government services (closed book)\n"] + tbl("gov") + ["", "## Consumer support (answer from the page)\n"] + tbl("consumer") + [
          "", "## How answers were scored\n", f"- By code (number, fee, duration, document list or yes/no): {byhow['code']} of {tot_runs} scored runs.",
          f"- By the judge (`{JUDGE}`): {byhow['judge']} runs. Harness errors left out: {n_he}.",
          f"- Judge vs second judge (`{JUDGE2}`) on a random sample: {agree}/{len(both)} identical verdicts" + (f" ({100 * agree / len(both):.0f}%)." if both else "."), cc_line,
          f"- Judge vs the human-labelled subset: {hl}", "",
          "## For a human check\n", f"**English and Arabic gold answers that disagree** ({len(cand)} pairs by the rule: yes/no differs, or the numbers in the gold sentences differ; the issue counted 13, this rule is broader). A gold answer that is wrong in one language makes the gap look bigger or smaller for that pair. Full list with reasons: `results/human_check_pairs.csv`.", ""]
    md += [f"- {p['pair_id']}: " + "; ".join(w_) for p, w_ in cand if p["exact"] and p["en"]["exact"]["type"] == "yesno" and any("yes/no" in x for x in w_)]
    af_c = [f"{pid} {lang.upper()} ({nf}/{n} wrong)" for pid, lang, nf, n in cf_]; af_g = [p for p in allfail if p["track"] == "gov"]
    md += ["", f"**Consumer-track items (pair + language) that every model, or all but one, gets wrong:** {len(af_c)}: " + (", ".join(af_c) or "none") + f". On the closed-book track {len(af_g)} pairs are failed by every model (expected for obscure facts); they are in `results/human_check_pairs.csv`. All are listed for a human to check the gold answer and the question, none is dropped.", ""]
    md += ["## Totals\n", f"- Scored runs: {tot_runs}; answer cost incl. reruns ${ans_cost:.2f}; judging cost ${jcost:.2f} (OpenRouter-reported).", "",
           "## Models that could not be run\n", "Searched the OpenRouter model list on the run date; none of these Arabic-first models is offered there: " + "; ".join(UNAVAILABLE) + ".", "",
           "## Limits\n", "- Arabic questions and gold answers were written by a model from the Arabic page; no Arabic reader has checked them.",
           "- Gold answers are condensed by a model from the page; a few may be incomplete. Pages were read on the date in each item and change over time.",
           "- One run at temperature 0. The code yes/no scorer treats a refusal as neither yes nor no; an answer like \"لا بأس\" (no problem) would be read as no.",
           "- Consumer-track help pages are used only as source text; retailer names are removed from the questions. These results say nothing about any company's product or service.", ""]
    with open(RES / "human_check_pairs.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["pair_id", "kind", "reason", "english_gold", "arabic_gold"])
        for p, w_ in cand: w.writerow([p["pair_id"], "gold answers disagree", "; ".join(w_), p["en"]["gold"], p["ar"]["gold"]])
        for p in allfail: w.writerow([p["pair_id"], "every model fails", "no scored answer correct in either language", p["en"]["gold"], p["ar"]["gold"]])
    mp = RES / "run_meta.json"; prev = json.loads(mp.read_text()) if mp.exists() else {}
    earlier = prev.get("earlier_run", prev if prev and "run" not in prev else None)
    jc = {j: round(sum(json.loads(l)["cost"] for l in judge_file(j).read_text().splitlines()), 4) if judge_file(j).exists() else 0 for j in (JUDGE, JUDGE2)}
    meta_out = {"run": "scaled", "date": time.strftime("%Y-%m-%d"), "models": models, "unavailable_on_openrouter": UNAVAILABLE,
                "pairs": dict(n_pairs), "languages": ["en", "ar"], "scored_runs": tot_runs, "scored_by_code": byhow["code"], "scored_by_judge": byhow["judge"],
                "judge": JUDGE, "judge2_sample": JUDGE2, "judge2_sample_size": len(both), "judge2_agreement": agree,
                "answer_cost_usd": round(ans_cost, 4), "answer_cost_usd_by_model": {m: round(sum(r["cost"] for r in rows if r["model"] == m), 4) for m in models},
                "judge_cost_usd": jc[JUDGE], "judge2_cost_usd": jc[JUDGE2], "total_cost_usd": round(ans_cost + jcost, 4), "scorer": "corrected 2026-11-17 (CHE-289); empty answers rerun, see arabic_gap.md", "harness_errors_left_out": n_he, "human_labelled_subset": "not yet labelled" if not human.exists() else "see arabic_gap.md"}
    if earlier: meta_out["earlier_run"] = earlier
    mp.write_text(json.dumps(meta_out, indent=1, ensure_ascii=False) + "\n")
    (RES / "arabic_gap.md").write_text("\n".join(md))
    import random
    pool = [r for r in rows if r["ok"] is not None]; random.Random(3).shuffle(pool)
    sel = [r for r in pool if r["lang"] == "ar"][:60] + [r for r in pool if r["lang"] == "en"][:40]
    with open(RES / "human_label_sheet.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["pair_id", "lang", "model", "question", "gold_answer", "model_answer", "scored_by", "auto_verdict", "human_verdict(correct/partial/incorrect)", "human_note"])
        for r in sel:
            p = byid[r["pair_id"]]; a = ans_by[(r["pair_id"], r["lang"], r["model"])]["text"]
            w.writerow([r["pair_id"], r["lang"], r["model"], p[r["lang"]]["question"], p[r["lang"]]["gold"], a, r["how"], "correct" if r["ok"] else "not correct", "", ""])
    print("\n".join(md[:30]))

if __name__ == "__main__": main()
