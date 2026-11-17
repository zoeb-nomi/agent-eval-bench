#!/usr/bin/env python3
"""Run models through OpenRouter on both tracks in both languages, judge with a live model, write results.

Usage: OPENROUTER_API_KEY=... run_bench.py [--smoke] [--models a,b] [--judge m] [--judge2 m]
Tracks: gov (closed-book UAE government-services knowledge) and consumer (answer from the supplied help-page text).
Only items present in both languages are scored (paired), so the gap compares the same question.
Raw answers: results/raw/<model>/<track>_<lang>.jsonl ; judgements: results/judgements/<judge>/...
"""
import json, os, sys, re, time, argparse, pathlib, concurrent.futures as cf
import requests
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent; Q = ROOT / "questions"; R = ROOT / "results"
MODELS = ["anthropic/claude-haiku-5.5", "openai/gpt-6.1-terra", "deepseek/deepseek-v4.1-flash-1017",
          "qwen/qwen4-max", "mistralai/mistral-large-4-0", "moonshotai/kimi-k3.1-pro"]
JUDGE, JUDGE2 = "anthropic/claude-sonnet-5.5", "deepseek/deepseek-v4.1-flash-1017"
URL = "https://openrouter.ai/api/v1/chat/completions"

def call(model, prompt, max_tokens, key, system=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    for attempt in range(3):
        r = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, timeout=180,
                          json={"model": model, "messages": msgs, "temperature": 0, "max_tokens": max_tokens, "usage": {"include": True}})
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code != 200:
            return {"error": f"{r.status_code} {r.text[:200]}", "text": "", "cost": 0.0}
        j = r.json(); u = j.get("usage", {})
        return {"text": (j["choices"][0]["message"].get("content") or ""), "cost": float(u.get("cost") or 0),
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")}
    return {"error": "gave up after 3 tries", "text": "", "cost": 0.0}

def load(track, lang):
    f = Q / (f"{lang}.jsonl" if track == "gov" else f"consumer_{lang}.json")
    return {x["id"][-3:]: x for x in json.loads(f.read_text())}

def paired(track):
    en, ar = load(track, "en"), load(track, "ar")
    return [(k, en[k], ar[k]) for k in sorted(en) if k in ar], sorted(set(en) ^ set(ar))

def answer_prompt(track, lang, item):
    lang_name = "English" if lang == "en" else "Arabic"
    if track == "gov":
        return (f"Answer this question about UAE government services accurately and concisely, in {lang_name}. "
                f"If you are not sure, say so rather than guessing.\n\nQuestion: {item['question']}")
    return (f"Below is the text of a public help page. Answer the customer's question using only that text, concisely, in {lang_name}. "
            f"If the page does not say, say so.\n\nHELP PAGE:\n{item['context']}\n\nQuestion: {item['question']}")

def judge_prompt(item, ans, lang):
    return f"""You are grading a model's answer against a reference answer taken from a public page.
The question and reference are in {'English' if lang=='en' else 'Arabic'}. Ignore language, style and length; judge only the facts.
Question: {item['question']}
Reference answer: {item['expected_answer']}
Model answer: {ans}

Verdict:
- correct: every key fact in the reference (numbers, days, fees, conditions) is present and nothing contradicts it
- partial: some key facts present, some missing or wrong
- incorrect: key facts wrong, contradicted, missing, or the model declines to answer
Reply with JSON only: {{"verdict":"correct|partial|incorrect","reason":"<one short sentence in English>"}}"""

def parse_verdict(t):
    m = re.search(r'"verdict"\s*:\s*"(correct|partial|incorrect)"', t)
    return m.group(1) if m else "unparsed"

def run_answers(models, key, smoke):
    jobs = []
    for model in models:
        for track in ("gov", "consumer"):
            pairs, _ = paired(track)
            if smoke: pairs = pairs[:1]
            for lang_i, lang in ((1, "en"), (2, "ar")):
                for p in pairs: jobs.append((model, track, lang, p[0], p[lang_i]))
    def one(j):
        model, track, lang, k, item = j
        out = R / "raw" / model.replace("/", "__") / f"{track}_{lang}.jsonl"
        res = call(model, answer_prompt(track, lang, item), 2500, key)
        return out, {"id": item["id"], "pair": k, "model": model, "track": track, "lang": lang, "question": item["question"], **res}
    results = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for out, rec in ex.map(one, jobs): results.setdefault(out, []).append(rec)
    for out, recs in results.items():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
    return sum(r["cost"] for rs in results.values() for r in rs)

def judge_all(judge, key, models, smoke):
    jobs = []
    for model in models:
        for track in ("gov", "consumer"):
            for lang in ("en", "ar"):
                f = R / "raw" / model.replace("/", "__") / f"{track}_{lang}.jsonl"
                ref = load(track, lang)
                for line in f.read_text().splitlines():
                    rec = json.loads(line); jobs.append((judge, rec, ref[rec["id"][-3:]]))
    def one(j):
        judge, rec, item = j
        res = call(judge, judge_prompt(item, rec["text"], rec["lang"]), 600, key)
        return {"id": rec["id"], "model": rec["model"], "track": rec["track"], "lang": rec["lang"], "pair": rec["pair"],
                "verdict": parse_verdict(res["text"]) if not res.get("error") else "unparsed", "judge_raw": res["text"], "cost": res["cost"]}
    with cf.ThreadPoolExecutor(8) as ex: out = list(ex.map(one, jobs))
    d = R / "judgements"; d.mkdir(parents=True, exist_ok=True)
    (d / f"{judge.replace('/', '__')}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true"); ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--judge", default=JUDGE); ap.add_argument("--judge2", default=JUDGE2)
    ap.add_argument("--judge-only", action="store_true")
    a = ap.parse_args(); key = os.environ["OPENROUTER_API_KEY"]
    models = a.models.split(",")
    if a.smoke:
        global R; R = pathlib.Path(os.environ.get("TMPDIR", ".")) / "smoke_results"
    cost_a = 0.0 if a.judge_only else run_answers(models, key, a.smoke)
    j1 = judge_all(a.judge, key, models, a.smoke); j2 = judge_all(a.judge2, key, models, a.smoke)
    meta = {"answer_cost_usd": cost_a, "judge_cost_usd": sum(r["cost"] for r in j1), "judge2_cost_usd": sum(r["cost"] for r in j2),
            "models": models, "judge": a.judge, "judge2": a.judge2, "date": time.strftime("%Y-%m-%d")}
    (R / "run_meta.json").write_text(json.dumps(meta, indent=1)); print(meta)

if __name__ == "__main__": main()
