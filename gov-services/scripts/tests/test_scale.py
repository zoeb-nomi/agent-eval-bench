import json, pathlib, sys, subprocess, tempfile, shutil
HERE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HERE / "scripts"))
from common import norm, score_exact, find_dups, wilson
import run_scale

def test_norm_arabic_digits_and_diacritics():
    assert norm("١٤ يومًا") == "14 يوما"
    assert norm("1,500") == "1500"

def test_exact_number_en_ar():
    ex = {"type": "number", "values": ["14"]}
    assert score_exact(ex, "Within 14 days of delivery.", "en")
    assert score_exact(ex, "خلال ١٤ يومًا من التسليم", "ar")
    assert not score_exact(ex, "Within 7 days.", "en")
    assert not score_exact(ex, "Within 140 days", "en")   # 14 must not match inside 140

def test_exact_yesno():
    assert score_exact({"type": "yesno", "values": ["yes"]}, "Yes, you can.", "en")
    assert not score_exact({"type": "yesno", "values": ["yes"]}, "No, you cannot.", "en")
    assert score_exact({"type": "yesno", "values": ["no"]}, "No. Headphones are excluded.", "en")
    assert score_exact({"type": "yesno", "values": ["yes"]}, "نعم، يمكنك ذلك.", "ar")
    assert score_exact({"type": "yesno", "values": ["no"]}, "لا، لا يمكن.", "ar")

def test_exact_list():
    assert score_exact({"type": "list", "values": ["passport", "photo"]}, "You need a Passport and a photo.", "en")
    assert not score_exact({"type": "list", "values": ["passport", "photo"]}, "A passport only", "en")

def test_dups():
    qs = ["How long is the learner permit valid?", "how long is the learner permit valid", "Within how many days can unopened items be returned to this retailer?",
          "Within how many days can this retailer's unopened items be returned?", "What is the minimum age for a learner permit?"]
    d = find_dups(qs)
    assert 1 in d and d[1][1] == 1.0          # exact after normalisation
    assert 3 in d                              # near duplicate
    assert 0 not in d and 2 not in d and 4 not in d

def test_wilson_interval_width_at_500():
    lo, hi = wilson(250, 500); assert 0.04 < (hi - lo) / 2 < 0.05      # about plus or minus 4.4 points at n=500

def test_build_from_fixture_pages():
    with tempfile.TemporaryDirectory() as t:
        out = pathlib.Path(t) / "out"; shutil.copytree(HERE / "scripts" / "fixtures" / "gen_cache", out / "gen_cache")   # cached generations: no model call
        r = subprocess.run([sys.executable, str(HERE / "scripts" / "build_sets.py"), "--pages-dir", str(HERE / "scripts" / "fixtures" / "pages"), "--out", str(out), "--target", "10"],
                           capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "OPENROUTER_API_KEY": "none"})
        assert r.returncode == 0, r.stderr
        gov = [json.loads(l) for l in (out / "pairs_gov.jsonl").read_text().splitlines()]
        con = [json.loads(l) for l in (out / "pairs_consumer.jsonl").read_text().splitlines()]
        assert len(gov) == 1 and gov[0]["exact"] and gov[0]["en"]["exact"]["values"] == ["6"]     # item 2 dropped: Arabic page lacks it... returned null
        assert len(con) == 1                                                                         # the second retailer's duplicate is dropped
        assert gov[0]["source_url_en"] != gov[0]["source_url_ar"] and gov[0]["date_read"] and gov[0]["ar"]["gold"]
        rep = json.loads((out / "dedupe_report.json").read_text())
        assert rep["consumer"]["dropped_total"] == 1 and rep["gov"]["arabic_missing_fact"] == 1

def test_run_cache_is_resumable(tmp_path, monkeypatch):
    monkeypatch.setattr(run_scale, "RES", tmp_path)
    ps = [{"pair_id": "GOV-0001", "track": "gov", "exact": True, "en": {"question": "q", "gold": "6", "exact": {"type": "number", "values": ["6"]}},
           "ar": {"question": "س", "gold": "6", "exact": {"type": "number", "values": ["6"]}}}]
    calls = []
    monkeypatch.setattr(run_scale, "call", lambda m, p, mt, k, **kw: calls.append(p) or {"text": "6", "cost": 0.01, "latency_s": 1.0})
    run_scale.run_answers(["m/x"], ps, "k"); assert len(calls) == 2
    run_scale.run_answers(["m/x"], ps, "k"); assert len(calls) == 2        # second run pays for nothing
