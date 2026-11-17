#!/usr/bin/env python3
"""Build the scaled pair sets from the page list.

  python scripts/build_sets.py [--pages-dir cache/pages] [--out questions] [--target 500] [--gen-model M] [--fixture]

Flow (every step is cached, so a rerun costs nothing and gives the same sets):
 1. read fetched page pairs (pages.json -> cache/pages, see pages.py)
 2. English question + short gold answer written from the ENGLISH page (LLM, cached in questions/gen_cache/en/)
 3. Arabic question + gold written from the ARABIC page for the same fact; not a translation of the English
    question (LLM, cached in questions/gen_cache/ar/). The fact is dropped if the Arabic page does not state it.
 4. checks by code: exact values must literally occur in the gold answer and in that language's page text
 5. duplicate / near-duplicate check (exact and word-3-gram Jaccard >= 0.6), per language; a pair is dropped if either side is a duplicate
 6. pick up to --target pairs per track, round-robin over pages/categories, at most 2 per page
Outputs: questions/pairs_<track>.jsonl, questions/dedupe_report.json
"""
import argparse, collections, concurrent.futures as cf, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import call, parse_json, find_dups, norm, score_exact
ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN_MODEL = "anthropic/claude-haiku-5.5"
MAXCH = 7000

EN_PROMPT = """You write test questions for a benchmark. Source: an official public page in English.
Track: {track_desc}
Write up to {k} question(s) whose answer is stated explicitly on the page. Rules:
- {rule}
- One fact each, different facts across questions. Prefer specific facts: numbers, fees, durations, ages, document lists, yes/no eligibility.
- The gold answer is short (one sentence or less), copied or condensed from the page, nothing added.
- answer_type: "number" if the answer is one or two numbers (fee, days, age, amount), "yesno" if the answer is yes or no, "list" if the answer is a list of 2-5 items, else "text".
- exact_values: for number: the numbers as plain digits (e.g. ["14"], ["5000"]); for yesno: ["yes"] or ["no"]; for list: 2-5 short key words copied from the gold answer; for text: [].
Reply with JSON only: {{"items":[{{"question":"","gold":"","answer_type":"","exact_values":[],"fact":"<the fact in 8 words>"}}]}}
If the page states nothing suitable reply {{"items":[]}}.

PAGE:
{page}"""

AR_PROMPT = """You write Arabic test questions for a benchmark, from an official public Arabic page.
Below is a FACT (described in English) and the Arabic page. Write ONE question in natural Modern Standard Arabic, as an Arabic speaker would ask it, about that fact. Do not translate any English wording; use the Arabic page's own terms.
{rule_ar}
The gold answer must come from the Arabic page text only, short (one sentence or less), in Arabic.
If the Arabic page does not state this fact, reply {{"item":null}}.
answer_type "{atype}"; exact_values: for number the numbers as plain ASCII digits as stated on the Arabic page; for yesno ["yes"] or ["no"]; for list 2-5 short Arabic key words copied from your gold answer; for text [].
Reply with JSON only: {{"item":{{"question":"","gold":"","answer_type":"{atype}","exact_values":[]}}}}

FACT: {fact}
English question (for the topic only, do not translate it): {qen}

ARABIC PAGE:
{page}"""

TRACK = {"gov": ("UAE government services, answered WITHOUT the page in front of the reader (closed book).",
                 "Each question must stand alone and name the UAE service or topic explicitly (no 'this page', no 'the above'); it must have one clear answer that does not depend on a specific emirate unless the question names it.",
                 "يجب أن يكون السؤال مستقلاً ويذكر الخدمة أو الموضوع في دولة الإمارات صراحة (دون عبارات مثل «هذه الصفحة»)."),
         "consumer": ("customer support (returns, delivery, refunds, orders, payments) of a UAE retailer; the reader will be given the page text.",
                      "Never name the retailer or any brand; say 'this retailer'. Each question must be answerable from the page text alone.",
                      "لا تذكر اسم المتجر أو أي علامة تجارية، وقل «هذا المتجر». يجب أن يمكن الإجابة من نص الصفحة وحدها.")}

def cached(path, fn):
    if path.exists(): return json.loads(path.read_text())
    res = fn(); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(res, ensure_ascii=False)); return res

def gen_en(page, model, out):
    k = 2 if page["track"] == "gov" else (2 if len(page["text_en"]) > 1500 else 1)
    td, rule, _ = TRACK[page["track"]]
    def run():
        r = call(model, EN_PROMPT.format(track_desc=td, k=k, rule=rule, page=page["text_en"][:MAXCH]), 1500, json_mode=True)
        j = parse_json(r["text"]) or {}
        return {"items": j.get("items", []) if isinstance(j, dict) else [], "cost": r["cost"], "error": r.get("error")}
    return cached(out / "gen_cache" / "en" / f"{page['id']}.json", run)

def gen_ar(page, item, idx, model, out):
    _, _, rule_ar = TRACK[page["track"]]
    def run():
        r = call(model, AR_PROMPT.format(rule_ar=rule_ar, atype=item["answer_type"], fact=item.get("fact", ""), qen=item["question"],
                                         page=page["text_ar"][:MAXCH]), 1200, json_mode=True)
        j = parse_json(r["text"]) or {}
        return {"item": j.get("item") if isinstance(j, dict) else None, "cost": r["cost"], "error": r.get("error")}
    return cached(out / "gen_cache" / "ar" / f"{page['id']}_{idx}.json", run)

def valid_exact(atype, values, gold, page_text, lang):
    """exact flag survives only if the values are in the gold answer and in that language's page."""
    if atype not in ("number", "yesno", "list") or not values: return None
    if atype == "yesno":
        return {"type": "yesno", "values": [values[0]]} if norm(values[0]) in ("yes", "no", "نعم", "لا") else None
    ex = {"type": atype, "values": [str(v) for v in values]}
    if atype == "number" and not all(re.fullmatch(r"\d+(\.\d+)?", norm(v)) for v in ex["values"]): return None
    g, p = norm(gold), norm(page_text)
    if atype == "number":
        from common import NUM
        gn, pn = set(NUM.findall(g)), set(NUM.findall(p))
        return ex if all(norm(v) in gn and norm(v) in pn for v in ex["values"]) else None
    return ex if all(norm(v) in g and norm(v) in p for v in ex["values"]) else None

def category(page):
    if page["track"] == "gov":
        m = re.search(r"/information-and-services/([^/]+)", page["en"]); return m.group(1) if m else "other"
    return page.get("portal", "other")

def build_track(track, pages, out, model, target, workers=12):
    pages = [p for p in pages if p["track"] == track]
    with cf.ThreadPoolExecutor(workers) as ex:
        en = list(ex.map(lambda p: gen_en(p, model, out), pages))
        jobs = [(p, i, it) for p, g in zip(pages, en) for i, it in enumerate(g["items"][:2])
                if isinstance(it, dict) and it.get("question") and it.get("gold")]
        ar = list(ex.map(lambda j: gen_ar(j[0], j[2], j[1], model, out), jobs))
    cands, drops = [], collections.Counter()
    for (p, i, it), a in zip(jobs, ar):
        ai = a.get("item")
        if not isinstance(ai, dict) or not ai.get("question") or not ai.get("gold"): drops["arabic page lacks the fact"] += 1; continue
        ex_en = valid_exact(it.get("answer_type"), it.get("exact_values") or [], it["gold"], p["text_en"], "en")
        ex_ar = valid_exact(it.get("answer_type"), ai.get("exact_values") or [], ai["gold"], p["text_ar"], "ar")
        exact = bool(ex_en and ex_ar)
        if exact and ex_en["type"] == "number" and sorted(map(norm, ex_en["values"])) != sorted(map(norm, ex_ar["values"])):
            exact = False; drops["exact demoted: numbers differ between languages"] += 1
        cands.append({"page": p, "idx": i, "category": category(p),
                      "en": {"question": it["question"].strip(), "gold": it["gold"].strip(), "exact": ex_en if exact else None},
                      "ar": {"question": ai["question"].strip(), "gold": ai["gold"].strip(), "exact": ex_ar if exact else None}})
    n0 = len(cands)
    d_en = find_dups([c["en"]["question"] for c in cands]); d_ar = find_dups([c["ar"]["question"] for c in cands])
    # gold-level near duplicates catch different wording of the same fact across retailers
    d_g = find_dups([c["en"]["question"] + " " + c["en"]["gold"] for c in cands], tri=0.5, uni=0.75)
    dropped = set(d_en) | set(d_ar) | set(d_g)
    kept = [c for i, c in enumerate(cands) if i not in dropped]
    report = {"generated": n0, "arabic_missing_fact": drops["arabic page lacks the fact"], "dropped_duplicate_en_question": len(d_en),
              "dropped_duplicate_ar_question": len(d_ar), "dropped_near_duplicate_fact": len(d_g), "dropped_total": len(dropped), "kept_before_selection": len(kept),
              "examples": [{"dropped": cands[i]["en"]["question"], "kept": cands[j]["en"]["question"], "similarity": s}
                           for i, (j, s) in list(d_g.items())[:5]]}
    # pick: round-robin over categories, <=2 per page
    by_cat = collections.defaultdict(list)
    for c in kept: by_cat[c["category"]].append(c)
    order, per_page, chosen = sorted(by_cat), collections.Counter(), []
    while len(chosen) < target and any(by_cat.values()):
        for cat in order:
            while by_cat[cat]:
                c = by_cat[cat].pop(0)
                if per_page[c["page"]["id"]] < 2: per_page[c["page"]["id"]] += 1; chosen.append(c); break
            if len(chosen) >= target: break
    report["selected"] = len(chosen); report["exact_items"] = sum(bool(c["en"]["exact"]) for c in chosen)
    rows = []
    for n, c in enumerate(sorted(chosen, key=lambda c: (c["page"]["id"], c["idx"])), 1):
        p = c["page"]
        row = {"pair_id": f"{track.upper()}-{n:04d}", "track": track, "category": c["category"], "source_url_en": p["en"], "source_url_ar": p["ar"],
               "date_read": p["date_read"], "exact": bool(c["en"]["exact"]), "en": c["en"], "ar": c["ar"],
               "arabic_basis": "written from the Arabic page, not translated", "arabic_checked_by_reader": False}
        if track == "consumer": row["context_en"], row["context_ar"] = p["text_en"][:MAXCH], p["text_ar"][:MAXCH]
        rows.append(row)
    (out / f"pairs_{track}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    gen_cost = sum(g["cost"] for g in en) + sum(a["cost"] for a in ar)
    report["generation_cost_usd"] = round(gen_cost, 4); report["pages_used"] = len({c["page"]["id"] for c in chosen})
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-dir", default=str(ROOT / "cache" / "pages")); ap.add_argument("--out", default=str(ROOT / "questions"))
    ap.add_argument("--target", type=int, default=500); ap.add_argument("--gen-model", default=GEN_MODEL)
    ap.add_argument("--tracks", default="gov,consumer"); a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pages = [json.loads(f.read_text()) for f in sorted(pathlib.Path(a.pages_dir).glob("*.json"))]; pages = [p for p in pages if p.get("ok")]
    rep = {t: build_track(t, pages, out, a.gen_model, a.target) for t in a.tracks.split(",")}
    (out / "dedupe_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False)); print(json.dumps(rep, indent=1, ensure_ascii=False)[:3000])

if __name__ == "__main__": main()
