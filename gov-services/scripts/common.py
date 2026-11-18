"""Shared helpers: OpenRouter call, Arabic-aware text normalisation, the code scorer, near-duplicate check."""
import json, os, re, time, unicodedata
import requests
URL = "https://openrouter.ai/api/v1/chat/completions"

def call(model, prompt, max_tokens, key=None, system=None, temperature=0, json_mode=False, retries=4, extra=None):
    key = key or os.environ["OPENROUTER_API_KEY"]
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens, "usage": {"include": True}}
    if extra: body.update(extra)
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


YES_W_EN = {"yes", "yeah", "yep", "correct", "absolutely", "sure"}
NO_W_EN = {"no", "not", "nope", "cannot", "cant", "never", "dont", "doesnt", "isnt", "arent", "wont", "wasnt", "shouldnt", "couldnt", "wouldnt", "didnt", "cant", "cannot"}
YES_W_AR = {"نعم", "اجل", "بلي"}
NO_W_AR = {"لا", "كلا", "ليس", "ليست", "لن", "لم"}
# declining to answer is neither yes nor no ("I am not sure", "لا أعلم")
HEDGE = re.compile(r"\b(not sure|unsure|don't know|do not know|dont know|no information|not specified|does not say|doesn't say|cannot confirm|can't confirm|not certain|i'm not|i am not)\b"
                   r"|لست متاكد|لا اعلم|لا املك|لا اعرف|غير متاكد|لا يوجد ما يشير|لا تذكر|لا يذكر|لا استطيع")
TOK = re.compile(r"[\w']+")

def _word_class(tok, lang):
    """'yes', 'no' or None for one normalised token. Strips a leading و/ف (and) that Arabic glues on: ولا, فنعم."""
    t = tok.replace("'", "")
    yes, no = (YES_W_EN, NO_W_EN) if lang == "en" else (YES_W_AR, NO_W_AR)
    for c in ([t] if lang == "en" else [t, t[1:] if t[:1] in "وف" else t]):
        if c in yes: return "yes"
        if c in no: return "no"
    return None

def yesno_verdict(answer, lang):
    """'yes' | 'no' | None. Punctuation (Arabic and English, including the Arabic comma) is dropped by tokenising on word characters.
    A hedge or refusal is None. Otherwise the FIRST word decides; if the first word is neither, the first yes/no word of the
    first sentence decides. A later no-word never flips an earlier yes."""
    a = norm(answer)
    a = re.sub(r"^[^\w]+", "", a)                       # leading bullets, **, quotes, emoji
    if HEDGE.search(re.split(r"[.!?؟\n]", a, maxsplit=1)[0]): return None
    toks = TOK.findall(a)
    if not toks: return None
    first = _word_class(toks[0], lang)
    if first: return first
    sent = TOK.findall(re.split(r"[.!?؟\n]", a, maxsplit=1)[0][:200])
    for t in sent:
        c = _word_class(t, lang)
        if c: return c
    return None

_PRE = re.compile(r"^(?:[وف]?[بكل]?ال|[وف]?لل)(?=\w{2})")
def list_norm(t):
    """norm + slash and 'or' (or / او) unified to a space + Arabic definite article and the one-letter prepositions/conjunction stripped per word."""
    t = norm(t).replace("/", " ")
    t = re.sub(r"(?<!\w)(?:or|او)(?!\w)", " ", t)
    out = []
    for w in re.findall(r"\w+", t):
        w2 = _PRE.sub("", w)
        if w2 == w and len(w) >= 5 and w[0] in "وبلفك" and re.match("[؀-ۿ]", w): w2 = w[1:]
        out.append(w2)
    return " " + " ".join(out) + " "

def score_exact(ex, answer, lang):
    """Code scorer for exact items. ex = {"type": number|yesno|list, "values": [...]}. Returns True/False."""
    a = norm(answer)
    if ex["type"] == "number":
        got = set(NUM.findall(a)); want = [str(norm(v)) for v in ex["values"]]
        want = [w.rstrip("0").rstrip(".") if "." in w else w for w in want]
        got = {g.rstrip("0").rstrip(".") if "." in g else g for g in got}
        return all(w in got for w in want)
    if ex["type"] == "yesno":
        want = norm(ex["values"][0]) in ("yes", "نعم", "true")
        return yesno_verdict(answer, lang) == ("yes" if want else "no")
    if ex["type"] == "list":
        la = list_norm(answer)
        return all(list_norm(v).strip() in la for v in ex["values"])
    raise ValueError(ex["type"])

def score_exact_legacy(ex, answer, lang):
    """LEGACY scorer (first scaled report); kept only to show old numbers beside corrected ones. Has the comma bug. ex = {"type": number|yesno|list, "values": [...]}. Returns True/False."""
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
