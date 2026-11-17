#!/usr/bin/env python3
"""Run models on every pair in both languages through OpenRouter; judge the non-exact ones; resumable and cached.

  OPENROUTER_API_KEY=... python scripts/run_scale.py pilot            # 50-item pilot, prints projected cost, stops above the cap
  OPENROUTER_API_KEY=... python scripts/run_scale.py full             # refuses unless pilot projection <= cap, or --approved-usd N (Zoeb's decision)
  python scripts/run_scale.py full --approved-usd 40
Cache: results/raw/<model>.jsonl (one line per pair x language; the key is never re-asked) and results/judgements/<judge>.jsonl.
A stopped run continues without paying twice. Errors are not cached, so they are retried on resume.
"""
import argparse, collections, concurrent.futures as cf, json, os, pathlib, random, sys, threading
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import call, parse_json, score_exact
ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
CAP_USD = 10.0
# Zoeb, 17 Nov: cheaper plan, 10 USD ceiling; gemini-4-hydrogen, kimi-k3.1-pro and mistral-large-4-0 dropped after the pilot
MODELS = ["anthropic/claude-haiku-5.5", "openai/gpt-6.1-terra", "deepseek/deepseek-v4.1-flash-1017", "qwen/qwen4-max",
          "minimax/minimax-m3.1-flash", "tencent/hy4-flash", "meta/muse-ember"]
JUDGE, JUDGE2 = "deepseek/deepseek-v4.1-flash-1017", "anthropic/claude-sonnet-5.5"   # cheap judge for all non-exact; Sonnet on a sample of 300
SONNET_SAMPLE = 300
LOCK = threading.Lock()

def pairs(q=ROOT / "questions"):
    out = []
    for t in ("gov", "consumer"):
        f = q / f"pairs_{t}.jsonl"
        if f.exists(): out += [json.loads(l) for l in f.read_text().splitlines()]
    return out

def items(ps):
    for p in ps:
        for lang in ("en", "ar"): yield p, lang

def answer_prompt(p, lang):
    ln = "English" if lang == "en" else "Arabic"
    rules = (f"Answer in {ln}, in at most two sentences. Write every number as digits. "
             + ("If it is a yes/no question, begin with Yes or No." if lang == "en" else "If it is a yes/no question, begin with نعم or لا."))
    q = p[lang]["question"]
    if p["track"] == "gov":
        return f"Answer this question about UAE government services. {rules} If you are not sure, say so rather than guess.\n\nQuestion: {q}"
    return (f"Below is the text of a public help page. Answer the customer's question using only that text. {rules} If the page does not say, say so.\n\n"
            f"HELP PAGE:\n{p['context_' + lang]}\n\nQuestion: {q}")

def judge_prompt(p, lang, ans):
    return f"""You are grading a model's answer against a reference answer taken from an official page.
The question and reference are in {'English' if lang == 'en' else 'Arabic'}. Ignore language, style and length; judge only the facts.
Question: {p[lang]['question']}
Reference answer: {p[lang]['gold']}
Model answer: {ans}

Verdict:
- correct: every key fact in the reference (numbers, days, fees, conditions) is present and nothing contradicts it
- partial: some key facts present, some missing or wrong
- incorrect: key facts wrong, contradicted, missing, or the model declines to answer
Reply with JSON only: {{"verdict":"correct|partial|incorrect","reason":"<one short sentence in English>"}}"""

def read_cache(f):
    d = {}
    if f.exists():
        for l in f.read_text().splitlines():
            r = json.loads(l); d[(r["pair_id"], r["lang"])] = r
    return d

def append(f, rec):
    with LOCK:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a") as fh: fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

def raw_file(model): return RES / "raw" / (model.replace("/", "__") + ".jsonl")
def judge_file(j): return RES / "judgements" / (j.replace("/", "__") + ".jsonl")

def run_answers(models, ps, key, workers=16):
    todo = []; done_cost = 0.0
    for m in models:
        c = read_cache(raw_file(m)); done_cost += sum(r["cost"] for r in c.values())
        todo += [(m, p, lang) for p, lang in items(ps) if (p["pair_id"], lang) not in c]
    def one(j):
        m, p, lang = j
        r = call(m, answer_prompt(p, lang), 1500, key)
        if r.get("error"): return r["error"]
        append(raw_file(m), {"pair_id": p["pair_id"], "lang": lang, "track": p["track"], "model": m, "question": p[lang]["question"],
                             "text": r["text"], "cost": r["cost"], "latency_s": r["latency_s"], "prompt_tokens": r.get("prompt_tokens"),
                             "completion_tokens": r.get("completion_tokens"), "finish": r.get("finish")})
    errs = []; n = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        for e in ex.map(one, todo):
            n += 1
            if e: errs.append(e)
            if n % 200 == 0: print(f"  answers {n}/{len(todo)} errors {len(errs)}", flush=True)
    print(f"answers: {len(todo)} new calls, {len(errs)} errors (retried on resume); earlier cost ${done_cost:.3f}")
    return errs

def judge_jobs(models, ps, judge, sample=None):
    byid = {p["pair_id"]: p for p in ps}; jobs = []
    for m in models:
        for (pid, lang), r in read_cache(raw_file(m)).items():
            if pid not in byid: continue
            p = byid[pid]
            if p["exact"]: continue          # exact items are scored by code only
            jobs.append((m, p, lang, r))
    return jobs, None

def run_judge(judge, models, ps, key, sample=None, workers=16):
    """sample: None = every non-exact answer; float = that share of ALL answers (exact ones included) for cross-checks."""
    jobs, _ = judge_jobs(models, ps, judge, sample)
    cache = {(r["pair_id"], r["lang"], r["model"]) for r in map(json.loads, judge_file(judge).read_text().splitlines())} if judge_file(judge).exists() else set()
    if sample is not None:   # fixed random sample of `sample` answers (stable across resumes), then drop the cached ones
        jobs = sorted(jobs, key=lambda j: (j[1]["pair_id"], j[2], j[0])); random.Random(7).shuffle(jobs); jobs = jobs[:sample]
    jobs = [j for j in jobs if (j[1]["pair_id"], j[2], j[0]) not in cache]
    def one(j):
        m, p, lang, r = j
        x = call(judge, judge_prompt(p, lang, r["text"]), 500, key)
        if x.get("error"): return x["error"]
        j2 = parse_json(x["text"]) or {}; v = j2.get("verdict") if isinstance(j2, dict) else None
        append(judge_file(judge), {"pair_id": p["pair_id"], "lang": lang, "model": m, "verdict": v if v in ("correct", "partial", "incorrect") else "unparsed",
                                   "reason": (j2 or {}).get("reason", "") if isinstance(j2, dict) else "", "cost": x["cost"]})
    with cf.ThreadPoolExecutor(workers) as ex: errs = [e for e in ex.map(one, jobs) if e]
    print(f"judge {judge}: {len(jobs)} new calls, {len(errs)} errors")

def project(models, ps, pilot_ids):
    """projected full-run cost from the pilot answers actually paid for, per model x track x language."""
    total = 0.0; detail = {}
    n_all = collections.Counter((p["track"], lang) for p, lang in items(ps))
    for m in models:
        c = read_cache(raw_file(m)); by = collections.defaultdict(list)
        for (pid, lang), r in c.items():
            if pid in pilot_ids: by[(r["track"], lang)].append(r["cost"])
        for k, n in n_all.items():
            avg = sum(by[k]) / len(by[k]) if by[k] else 0.0; total += avg * n; detail[(m, k)] = avg
    nonexact = sum(not p["exact"] for p in ps) * 2 * len(models)
    judge_est = 0.00009 * nonexact + 0.0014 * SONNET_SAMPLE   # measured on the pilot: $0.000084 per cheap-judge call, $0.00136 per Sonnet call
    return total, judge_est, detail

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["pilot", "full"]); ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--approved-usd", type=float, default=None, help="Zoeb's decision to run above the cap; the new ceiling")
    ap.add_argument("--n-pilot", type=int, default=50); ap.add_argument("--questions", default=str(ROOT / "questions"))
    a = ap.parse_args(); key = os.environ["OPENROUTER_API_KEY"]; models = a.models.split(","); ps = pairs(pathlib.Path(a.questions))
    rnd = random.Random(11); pilot = [p for t in ("gov", "consumer") for p in rnd.sample([p for p in ps if p["track"] == t], min(a.n_pilot // 2, sum(p["track"] == t for p in ps)))]
    pid = {p["pair_id"] for p in pilot}
    if a.mode == "pilot" or not (RES / "pilot_projection.json").exists():
        print(f"pilot: {len(pilot)} items x 2 languages x {len(models)} models")
        run_answers(models, pilot, key)
        ans, jd, det = project(models, ps, pid); proj = ans + jd
        json.dump({"pilot_items": len(pilot), "projected_answers_usd": round(ans, 2), "projected_judging_usd": round(jd, 2), "projected_total_usd": round(proj, 2),
                   "cap_usd": CAP_USD, "per_model_usd_per_answer": {f"{m}|{t}|{l}": round(v, 5) for (m, (t, l)), v in det.items()}},
                  (RES / "pilot_projection.json").open("w"), indent=1)
        print(f"projected full run: answers ${ans:.2f} + judging ~${jd:.2f} = ${proj:.2f} (cap ${CAP_USD:.0f})")
        if a.mode == "pilot": 
            if proj > CAP_USD: print("ABOVE THE CAP: stop and ask for a decision (rerun `full --approved-usd N` to override)."); sys.exit(2)
            return
    proj = json.loads((RES / "pilot_projection.json").read_text())["projected_total_usd"]; ceiling = a.approved_usd if a.approved_usd is not None else CAP_USD
    if proj > ceiling:
        print(f"STOP: projected ${proj:.2f} is above ${ceiling:.0f}. Needs a decision; rerun with --approved-usd N."); sys.exit(2)
    run_answers(models, ps, key); run_judge(JUDGE, models, ps, key)
    run_judge(JUDGE2, models, ps, key, sample=SONNET_SAMPLE)   # Sonnet on 300 random non-exact answers: agreement with the cheap judge
    print("done; now run scripts/report_scale.py")

if __name__ == "__main__": main()
