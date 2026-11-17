#!/usr/bin/env python3
"""Page list + fetch + text extraction for the scaled gov-services benchmark.

`python scripts/pages.py discover` writes pages.json (the page list: one entry per page that exists officially in
English and Arabic). `python scripts/pages.py fetch` downloads both versions into cache/pages/ (gitignored) and keeps
only pairs whose Arabic text is really Arabic. Pages are used only as source text.
"""
import json, re, sys, time, hashlib, pathlib
import requests
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "pages"
LIST = ROOT / "pages.json"
UA = {"User-Agent": "Mozilla/5.0 (research-bot; benchmark source reading)"}
UAE = "https://u.ae"
ZENDESK = ["help.careem.com"]  # Zendesk help centres: same article id in en-us and ar
PORTALS = ["centrepointstores", "maxfashion", "homecentre", "splashfashions"]  # Freshdesk help centres, EN + AR articles

def get(url, retries=3):
    for i in range(retries):
        r = requests.get(url, headers=UA, timeout=40)
        if r.status_code == 429: time.sleep(10 * (i + 1)); continue
        return r
    return r

def arabic_ratio(t):
    letters = [c for c in t if c.isalpha()]
    return sum("؀" <= c <= "ۿ" for c in letters) / max(len(letters), 1)

def clean_text(html, kind):
    if kind == "zendesk":
        a = json.loads(html)["article"]; html = f"<main><h1>{a['title']}</h1>{a['body'] or ''}</main>"
    s = BeautifulSoup(html, "lxml")
    node = (s.select_one("#article-body") if kind == "support" else s.find("main")) or s
    for x in node(["script", "style", "nav", "header", "footer", "form", "noscript"]): x.decompose()
    t = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
    return t

def title_of(html):
    if html.startswith("{"): return json.loads(html)["article"]["title"]
    s = BeautifulSoup(html, "lxml"); h = s.find("h1") or s.find("h2") or s.find("title")
    return re.sub(r"\s+", " ", h.get_text(" ", strip=True)) if h else ""

def discover():
    out = []
    idx = get(UAE + "/en/information-and-services").text
    for p in sorted(set(re.findall(r'href="(/en/information-and-services/[^"#?]+)"', idx))):
        out.append({"id": "gov-" + hashlib.md5(p.encode()).hexdigest()[:8], "track": "gov", "kind": "u.ae",
                    "en": UAE + p, "ar": UAE + p.replace("/en/", "/ar/", 1)})
    for portal in PORTALS:
        base = f"https://helpae.{portal}.com"
        t = get(base + "/en/support/solutions").text
        arts = set()
        for f in sorted(set(re.findall(r"/en/support/solutions/folders/\d+", t))):
            arts |= set(re.findall(r"/en/support/solutions/articles/(\d+)", get(base + f).text)); time.sleep(0.3)
        for a in sorted(arts):
            out.append({"id": f"con-{portal}-{a}", "track": "consumer", "kind": "support", "portal": portal,
                        "en": f"{base}/en/support/solutions/articles/{a}", "ar": f"{base}/ar/support/solutions/articles/{a}"})
    for host in ZENDESK:
        url = f"https://{host}/api/v2/help_center/ar/articles.json?per_page=100"
        while url:
            j = get(url).json()
            for a in j["articles"]:
                out.append({"id": f"con-{host.split('.')[1]}-{a['id']}", "track": "consumer", "kind": "zendesk", "portal": host.split(".")[1],
                            "en": f"https://{host}/api/v2/help_center/en-us/articles/{a['id']}.json", "ar": f"https://{host}/api/v2/help_center/ar/articles/{a['id']}.json",
                            "url_en": f"https://{host}/hc/en-us/articles/{a['id']}", "url_ar": f"https://{host}/hc/ar/articles/{a['id']}"})
            url = j.get("next_page")
    LIST.write_text(json.dumps(out, indent=0, ensure_ascii=False)); print(len(out), "pages listed")

def fetch_one(e):
    f = CACHE / f"{e['id']}.json"
    if f.exists(): return None
    try:
        re_, ra = get(e["en"]), get(e["ar"])
        ok = re_.status_code == 200 and ra.status_code == 200
        ten, tar = (clean_text(re_.text, e["kind"]), clean_text(ra.text, e["kind"])) if ok else ("", "")
        ok = ok and len(ten) > 100 and len(tar) > 80 and arabic_ratio(tar) > 0.5 and arabic_ratio(ten) < 0.2
    except requests.RequestException:
        return None
    if e["kind"] == "zendesk": e = {**e, "en": e["url_en"], "ar": e["url_ar"]}
    rec = {**e, "ok": ok, "title_en": title_of(re_.text) if ok else "", "date_read": time.strftime("%Y-%m-%d"),
           "text_en": ten if ok else "", "text_ar": tar if ok else ""}
    f.write_text(json.dumps(rec, ensure_ascii=False)); return ok

def fetch(limit=None):
    import concurrent.futures as cf
    CACHE.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(fetch_one, json.loads(LIST.read_text())[:limit]))
    print("fetched ok", sum(r is True for r in res), "skipped", sum(r is False for r in res))

def load_cached():
    return [json.loads(f.read_text()) for f in sorted(CACHE.glob("*.json")) if json.loads(f.read_text())["ok"]]

if __name__ == "__main__":
    {"discover": discover, "fetch": fetch}[sys.argv[1]]()
