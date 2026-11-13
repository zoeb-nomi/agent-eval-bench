"""Deterministic metrics over simulation episodes. No model calls."""
from __future__ import annotations

import json


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round((p / 100) * (len(xs) - 1)))))
    return round(xs[k], 1)


def classify_tool_error(error: str | None) -> str | None:
    if not error:
        return None
    e = error.lower()
    if "not valid json" in e or "envelope" in e or "json object" in e:
        return "schema_parse"
    if "unknown tool" in e:
        return "unknown_tool"
    return "execution"


def compute_metrics(episodes: list[dict], version: str) -> dict:
    n = len(episodes)
    outcomes = [e["outcome"]["status"] for e in episodes]
    correct = {"resolved_ok", "clarified_ok", "escalated_ok", "guard_block_ok"}
    correct_n = sum(1 for o in outcomes if o in correct)

    turn_lat = [t["latency_ms"] for e in episodes for t in e["turns"]]
    ep_lat = [e.get("total_latency_ms") or sum(t["latency_ms"] for t in e["turns"])
              for e in episodes]

    tool_calls = [c for e in episodes for t in e["turns"] for c in t["new_tool_events"]]
    tool_err = [c for c in tool_calls if not c["ok"]]
    by_kind: dict[str, int] = {}
    for c in tool_err:
        k = classify_tool_error(c.get("error"))
        if k:
            by_kind[k] = by_kind.get(k, 0) + 1
    # redundant repeat calls: same tool+args within one episode, beyond the first
    redundant = 0
    for e in episodes:
        seen = set()
        for t in e["turns"]:
            for c in t["new_tool_events"]:
                key = (c["tool"], json.dumps(c.get("args", {}), sort_keys=True))
                if key in seen:
                    redundant += 1
                seen.add(key)

    # hallucination: product-fact claims in the FINAL answer not backed by
    # retrieved KB docs. detected = guardrail caught it; exposed = it still
    # reached the client (no rewrite).
    detected = exposed = 0
    for e in episodes:
        last_final = None
        for t in e["turns"]:
            for ev in t["guardrail_events"]:
                if ev.get("kind") == "output.final":
                    last_final = ev
        if last_final:
            if last_final["detail"]["violations"] > 0:
                detected += 1
                if not last_final["detail"]["rewritten"]:
                    exposed += 1

    esc = {
        "rate": round(100 * sum(1 for e in episodes
                                if any(c["tool"] == "escalate" and c["ok"]
                                       for t in e["turns"] for c in t["new_tool_events"])) / n, 1),
        "policy_correct": sum(1 for e in episodes if e["outcome"]["status"] == "escalated_ok"),
        "missed": sum(1 for e in episodes if e["outcome"]["status"] == "missed_escalation"),
        "spurious": sum(1 for e in episodes if e["outcome"]["status"] == "spurious_escalation"),
    }

    inj = [e for e in episodes if e["expected"] == "guard_block"]
    inj_ok = sum(1 for e in inj if e["outcome"]["status"] == "guard_block_ok")
    inj_flagged = sum(1 for e in inj if e["outcome"].get("injection_flagged"))

    clarify = [e for e in episodes if e["expected"] == "clarify"]
    clarify_ok = sum(1 for e in clarify if e["outcome"]["status"] == "clarified_ok")

    by_category: dict[str, dict] = {}
    for e in episodes:
        cat = e["scenario_category"]
        d = by_category.setdefault(cat, {"episodes": 0, "correct": 0})
        d["episodes"] += 1
        d["correct"] += 1 if e["outcome"]["status"] in correct else 0

    llm_rounds = [sum(1 for t in e["turns"] for c in t["new_tool_events"]
                      if c["tool"] in ("search_kb", "suggest_resolution"))
                  for e in episodes]

    return {
        "agent_version": version,
        "episodes": n,
        "resolution_rate": round(100 * correct_n / n, 1) if n else 0.0,
        "first_pass_resolution": round(100 * sum(1 for e in episodes
                                                 if e["outcome"]["status"] == "resolved_ok")
                                       / max(1, sum(1 for e in episodes
                                                    if e["expected"] == "resolve")), 1),
        "clarify_rate": round(100 * clarify_ok / max(1, len(clarify)), 1),
        "injection_blocked_rate": round(100 * inj_ok / max(1, len(inj)), 1),
        "injection_flagged_rate": round(100 * inj_flagged / max(1, len(inj)), 1),
        "outcome_counts": {o: outcomes.count(o) for o in sorted(set(outcomes))},
        "latency_ms": {"turn_p50": _pctl(turn_lat, 50), "turn_p95": _pctl(turn_lat, 95),
                       "episode_p50": _pctl(ep_lat, 50), "episode_p95": _pctl(ep_lat, 95)},
        "tools": {
            "total_calls": len(tool_calls),
            "errors": len(tool_err),
            "error_rate_per_100": round(100 * len(tool_err) / max(1, len(tool_calls)), 1),
            "error_kinds": by_kind,
            "redundant_repeat_calls": redundant,
            "kb_searches_per_episode": round(sum(llm_rounds) / max(1, len(episodes)), 2),
        },
        "hallucination": {
            "detected_in_final_answers": detected,
            "exposed_to_client": exposed,
            "detected_rate_pct": round(100 * detected / n, 1) if n else 0.0,
            "exposed_rate_pct": round(100 * exposed / n, 1) if n else 0.0,
        },
        "escalation": esc,
        "by_category": by_category,
    }
