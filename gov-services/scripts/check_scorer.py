#!/usr/bin/env python3
"""Check the code scorer against the cheap judge on a random sample of code-scored answers: 300 per language (seed 5, fixed, resumable).
Needs OPENROUTER_API_KEY for the judge calls only (about 600 calls, well under 0.1 USD). Output: results/judgements/code_check__<judge>.jsonl.
Only answers that are not harness errors are sampled. The report (report_scale.py) reads the file and prints the agreement."""
import concurrent.futures as cf, json, os, pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import call, parse_json
from run_scale import pairs, judge_prompt, append, judge_file, JUDGE, MODELS
from rescore import effective_answers
N = 330; CAP_USD = 0.1   # 330 drawn so that at least 300 per language remain after unparsed verdicts
def check_file(): return judge_file("code_check__" + JUDGE.replace("/", "__"))
def sample(ps):
    byid = {p["pair_id"]: p for p in ps}; ans = [a for a in effective_answers(MODELS) if byid[a["pair_id"]]["exact"] and not a["harness_error"]]; out = []
    for lang in ("en", "ar"):
        c = sorted((a for a in ans if a["lang"] == lang), key=lambda a: (a["pair_id"], a["model"])); random.Random(5).shuffle(c); out += c[:N]
    return out
def main():
    key = os.environ["OPENROUTER_API_KEY"]; ps = pairs(); byid = {p["pair_id"]: p for p in ps}; f = check_file()
    done = {(r["pair_id"], r["lang"], r["model"]) for r in map(json.loads, f.read_text().splitlines())} if f.exists() else set()
    jobs = [a for a in sample(ps) if (a["pair_id"], a["lang"], a["model"]) not in done]
    def one(a):
        if sum(json.loads(l)["cost"] for l in f.read_text().splitlines()) > CAP_USD if f.exists() else False: return "cap"
        x = call(JUDGE, judge_prompt(byid[a["pair_id"]], a["lang"], a["text"]), 500, key)
        if x.get("error"): return x["error"]
        j = parse_json(x["text"]); v = j.get("verdict") if isinstance(j, dict) else None
        append(f, {"pair_id": a["pair_id"], "lang": a["lang"], "model": a["model"], "verdict": v if v in ("correct", "partial", "incorrect") else "unparsed", "cost": x["cost"]})
    with cf.ThreadPoolExecutor(12) as ex: errs = [e for e in ex.map(one, jobs) if e]
    print(f"{len(jobs)} judge calls, {len(errs)} errors", errs[:2])
if __name__ == "__main__": main()
