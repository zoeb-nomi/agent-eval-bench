#!/usr/bin/env python3
"""Adds the public help-page excerpt (`context`) to consumer_en.json / consumer_ar.json from
a directory of saved page texts. Usage: build_context.py <pages_dir>
pages_dir holds samsung.txt, jumbo.txt, apple.txt, centrepoint.txt (plain text of the pages read 2026-11-17)."""
import json, sys, pathlib
P = pathlib.Path(sys.argv[1]); Q = pathlib.Path(__file__).resolve().parent.parent / "questions"
def key(u):
    return "samsung" if "samsung" in u else "jumbo" if "jumbo" in u else "apple" if "apple" in u else "centrepoint"
for f in ("consumer_en.json", "consumer_ar.json"):
    items = json.loads((Q / f).read_text())
    for it in items:
        # context is the English page text for every item (not every page exists in Arabic)
        it["context"] = (P / (key(it["source_url"]) + ".txt")).read_text()
    (Q / f).write_text(json.dumps(items, ensure_ascii=False, indent=1))
