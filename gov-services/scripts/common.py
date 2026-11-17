"""Shared helpers: OpenRouter call, Arabic-aware text normalisation, the code scorer, near-duplicate check."""
import json, os, re, time, unicodedata
import requests
URL = "https://openrouter.ai/api/v1/chat/completions"

def call(model, prompt, max_tokens, key=None, system=None, temperature=0, json_mode=False, retries=4):
    key = key or os.environ["OPENROUTER_API_KEY"]
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens, "usage": {"include": True}}
    if json_mode: body["response_format"] = {"type": "json_object"}
    t0 = time.time(); err = ""
    for i in range(retries):
        try:
            r = requests.post(URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=240)
        except requests.RequestException as e:
            err = str(e)[:150]; time.sleep(4 * (i + 1)); continue
        if r.status_code == 429 or r.status_code >= 500:
            err = f"{r.status_code}"; time.sleep(5 * (i + 1)); continue
        if r.status_code != 200:
            return {"error": f"{r.status_code} {r.text[:200]}", "text": "", "cost": 0.0, "latency_s": round(time.time() - t0, 2)}
        j = r.json(); u = j.get("usage") or {}
        ch = (j.get("choices") or [{}])[0]
        return {"text": (ch.get("message") or {}).get("content") or "", "cost": float(u.get("cost") or 0),
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                "finish": ch.get("finish_reason"), "latency_s": round(time.time() - t0, 2)}
    return {"error": f"gave up: {err}", "text": "", "cost": 0.0, "latency_s": round(time.time() - t0, 2)}

def parse_json(t):
    t = t.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m: t = m.group(1)
    try: return json.loads(t)
    except Exception:
        m = re.search(r"[\[{].*[\]}]", t, re.S)
        if m:
            try: return json.loads(m.group(0))
            except Exception: return None
    return None

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
def norm(t):
    """lowercase, Arabic digits to ASCII, strip diacritics/tatweel, unify alef/yaa/taa-marbuta, drop thousands commas."""
    t = unicodedata.normalize("NFKC", t or "").translate(AR_DIGITS).lower()
    t = re.sub(r"[ً-ٰٟـ]", "", t)
    t = re.sub("[إأآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه")
    t = re.sub(r"(?<=\d)[,،٬](?=\d{3})", "", t)
    t = t.replace("٪", "%")
    return re.sub(r"\s+", " ", t).strip()

NUM = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d])")
YES_EN, NO_EN = re.compile(r"\byes\b"), re.compile(r"\bno\b|\bnot\b|\bcannot\b|\bcan't\b|\bn't\b")
YES_AR, NO_AR = re.compile(r"(?<!\S)(نعم|اجل)(?!\S)|^نعم"), re.compile(r"(?<!\S)(لا|كلا)(?!\S)|لا يمكن|لا يجوز|لا يحق|ليس")

def score_exact(ex, answer, lang):
    """Code scorer for exact items. ex = {"type": number|yesno|list, "values": [...]}. Returns True/False."""
    a = norm(answer)
    if ex["type"] == "number":
        got = set(NUM.findall(a)); want = [str(norm(v)) for v in ex["values"]]
        want = [w.rstrip("0").rstrip(".") if "." in w else w for w in want]
        got = {g.rstrip("0").rstrip(".") if "." in g else g for g in got}
        return all(w in got for w in want)
    if ex["type"] == "yesno":
        head = re.split(r"[.!?؟\n]", a, maxsplit=1)[0][:160]
        want = norm(ex["values"][0]) in ("yes", "نعم", "true")
        yes = (YES_EN if lang == "en" else YES_AR).search(head); no = (NO_EN if lang == "en" else NO_AR).search(head)
        if want: return bool(yes) and not no
        return bool(no)
    if ex["type"] == "list":
        return all(norm(v) in a for v in ex["values"])
    raise ValueError(ex["type"])

def words(t): return set(re.findall(r"\w+", norm(t)))
def shingles(t, n=3):
    w = re.findall(r"\w+", norm(t)); return {" ".join(w[i:i + n]) for i in range(max(len(w) - n + 1, 1))}
def jaccard(a, b): return len(a & b) / max(len(a | b), 1)

def find_dups(texts, tri=0.6, uni=0.8):
    """Indices to drop: exact duplicates (after normalisation) and near duplicates (word 3-gram Jaccard >= tri, or
    word-set Jaccard >= uni, which catches re-ordered wording). The earlier item is kept.
    Returns {dropped_index: (kept_index, similarity)}."""
    sh = [shingles(t) for t in texts]; ws = [words(t) for t in texts]; n = [norm(t) for t in texts]; drop = {}; kept = []
    for i in range(len(texts)):
        hit = None
        for j in kept:
            if n[i] == n[j]: hit = (j, 1.0); break
            s3, s1 = jaccard(sh[i], sh[j]), jaccard(ws[i], ws[j])
            if s3 >= tri or s1 >= uni: hit = (j, round(max(s3, s1), 2)); break
        if hit: drop[i] = hit
        else: kept.append(i)
    return drop

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)
