#!/usr/bin/env python3
"""Rerun answers that came back empty (or cut off) because the token limit was hit. They are harness errors, never wrong answers.

  OPENROUTER_API_KEY=... python scripts/rerun_empty.py            # pilot of 8 per model, projects the total, stops above the cap
  python scripts/rerun_empty.py --go                              # runs the rest if the projection is under the cap
Attempt 1: reasoning off, same 1500-token limit. Attempt 2 (only if attempt 1 is still empty or errors): 6000 tokens, default reasoning.
Saved answers are never touched; reruns go to results/raw_rerun/<model>.jsonl (cached, resumable). Spend is counted from the files
and the run stops by itself at the cap. The non-empty answers are not re-asked; no other model is called here."""
import argparse, concurrent.futures as cf, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import call
from run_scale import pairs, read_cache, raw_file, answer_prompt, append, MODELS, RES
CAP_USD = 1.4          # answers rerun; the judge check (check_scorer.py, cap 0.1) brings the task total under 1.5
RERUN = RES / "raw_rerun"
def rerun_file(m): return RERUN / (m.replace("/", "__") + ".jsonl")
def is_bad(r): return (not (r.get("text") or "").strip()) or r.get("finish") == "length"
def spent():
    return sum(json.loads(l).get("cost", 0) for m in MODELS if rerun_file(m).exists() for l in rerun_file(m).read_text().splitlines())

def todo(models, limit=None):
    byid = {p["pair_id"]: p for p in pairs()}; out = []
    for m in models:
        done = read_cache(rerun_file(m)); bad = [(k, r) for k, r in sorted(read_cache(raw_file(m)).items()) if is_bad(r) and k not in done and k[0] in byid]
        out += [(m, byid[k[0]], k[1]) for k, r in bad[:limit]]
    return out

def one(j, key):
    m, p, lang = j; tot = 0.0; r = None
    for att, extra, mt in ((1, {"reasoning": {"enabled": False}}, 1500), (2, None, 6000)):
        if spent() > CAP_USD: return "cap reached"
        r = call(m, answer_prompt(p, lang), mt, key, extra=extra); tot += r.get("cost", 0)
        if not r.get("error") and r["text"].strip() and r.get("finish") != "length": break
    if r.get("error") and not r["text"]: return r["error"]
    append(rerun_file(m), {"pair_id": p["pair_id"], "lang": lang, "track": p["track"], "model": m, "text": r["text"], "cost": tot, "attempt": att,
                           "finish": r.get("finish"), "completion_tokens": r.get("completion_tokens"), "latency_s": r["latency_s"]})

def judge_reruns(key):
    """Judge the rerun answers of non-exact items with the same cheap judge (a rerun answer has no verdict yet). Cached in results/judgements/rerun__<judge>.jsonl."""
    from run_scale import judge_prompt, judge_file, JUDGE
    from common import parse_json
    f = judge_file("rerun__" + JUDGE.replace("/", "__")); done = set(read_cache(f)) if f.exists() else set(); byid = {p["pair_id"]: p for p in pairs()}
    jobs = [(m, byid[k[0]], k[1], r) for m in MODELS if rerun_file(m).exists() for k, r in read_cache(rerun_file(m)).items()
            if not byid[k[0]]["exact"] and (r["text"] or "").strip() and r.get("finish") != "length" and k not in done]
    def j1(j):
        m, p, lang, r = j; x = call(JUDGE, judge_prompt(p, lang, r["text"]), 500, key)
        if x.get("error"): return x["error"]
        d = parse_json(x["text"]); v = d.get("verdict") if isinstance(d, dict) else None
        append(f, {"pair_id": p["pair_id"], "lang": lang, "model": m, "verdict": v if v in ("correct", "partial", "incorrect") else "unparsed", "cost": x["cost"]})
    with cf.ThreadPoolExecutor(12) as ex: errs = [e for e in ex.map(j1, jobs) if e]
    print(f"judged {len(jobs)} rerun answers, errors {len(errs)}")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--go", action="store_true"); ap.add_argument("--judge", action="store_true"); ap.add_argument("--models", default=",".join(MODELS)); a = ap.parse_args()
    key = os.environ["OPENROUTER_API_KEY"]; models = a.models.split(",")
    if a.judge: return judge_reruns(key)
    total = len(todo(models)) + sum(len(read_cache(rerun_file(m))) for m in models)
    print(f"{total} answers to rerun in all")
    if not a.go:
        j = todo(models, 8); print(f"pilot: {len(j)} calls")
        with cf.ThreadPoolExecutor(8) as ex: errs = [e for e in ex.map(lambda x: one(x, key), j) if e]
        n = sum(len(read_cache(rerun_file(m))) for m in models)
        if errs: print("errors:", errs[:3]); 
        if n == 0: print("no pilot answer came back; stop"); sys.exit(1)
        proj = spent() / n * total; print(f"pilot spent ${spent():.4f} for {n} answers; projected total ${proj:.2f} (cap ${CAP_USD})")
        if proj > CAP_USD: print("ABOVE THE CAP: stop and ask for a decision"); sys.exit(2)
        return
    with cf.ThreadPoolExecutor(12) as ex: errs = [e for e in ex.map(lambda x: one(x, key), todo(models)) if e]
    judge_reruns(key)
    print(f"done; errors {len(errs)} (rerun resumes them); spent ${spent():.3f}")
if __name__ == "__main__": main()
