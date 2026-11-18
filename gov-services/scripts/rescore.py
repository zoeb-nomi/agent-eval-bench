"""Effective answers for scoring: the saved answer, replaced by its rerun when it was empty or cut off by the token limit.
An answer that is still empty (or cut off) has harness_error=True and is left out of every denominator; it is never counted wrong."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_scale import read_cache, raw_file
from rerun_empty import rerun_file, is_bad

def effective_answers(models):
    out = []
    for m in models:
        raw = read_cache(raw_file(m)); rr = read_cache(rerun_file(m))
        for (pid, lang), r in raw.items():
            rec = {"pair_id": pid, "lang": lang, "model": m, "track": r["track"], "orig_text": r["text"], "orig_bad": is_bad(r), "reran": False}
            x = rr.get((pid, lang))
            use = bool(r and is_bad(r) and x and not is_bad(x))
            t = x if use else r
            rec.update(text=t["text"], reran=use, harness_error=is_bad(t), cost=r["cost"] + (x["cost"] if x else 0), latency_s=r["latency_s"])
            out.append(rec)
    return out
