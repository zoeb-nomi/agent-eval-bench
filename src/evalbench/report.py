"""Markdown reports: findings from the eval layer on the baseline, and the
before/after delta between baseline (v0) and instrumented (v1) runs."""
from __future__ import annotations

import json
from pathlib import Path


def _load(run_dir: Path) -> dict:
    m = json.load(open(run_dir / "metrics.json"))
    eps = [json.loads(l) for l in open(run_dir / "episodes.jsonl")]
    cal = None
    cal_path = run_dir.parent / "evalset" / run_dir.name / "calibration.json"
    if cal_path.exists():
        cal = json.load(open(cal_path))
    return {"metrics": m, "episodes": eps, "calibration": cal}


def _md_table(rows: list[list], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def findings_md(run_dir: Path) -> str:
    """What the eval layer caught on the baseline that coarse logging missed."""
    data = _load(run_dir)
    m = data["metrics"]
    eps = data["episodes"]
    cal = data["calibration"]

    # examples of ungrounded final answers, for the report
    ungrounded_examples = []
    for e in eps:
        for t in e["turns"]:
            for ev in t["guardrail_events"]:
                if ev.get("kind") == "output.ungrounded_claims":
                    for v in ev["detail"]["violations"][:1]:
                        ungrounded_examples.append(
                            (e["episode_id"], e["scenario_id"], v["sentence"]))
    tool_err_examples = [c for e in eps for t in e["turns"] for c in t["new_tool_events"]
                         if not c["ok"]][:6]
    missed = [e for e in eps if e["outcome"]["status"] == "missed_escalation"]
    spurious = [e for e in eps if e["outcome"]["status"] == "spurious_escalation"]
    no_kb = [e for e in eps if e["outcome"]["status"] == "answered_without_kb"]

    lines = [
        f"# Findings: eval layer on the baseline run ({m['label']})",
        "",
        f"Run: {m['episodes']} episodes, {m['usage']['calls']} LLM calls, "
        f"{m['usage']['in_tokens'] + m['usage']['out_tokens']} tokens. "
        f"Coarse view (what the console showed before the eval layer): "
        f"resolution rate {m['resolution_rate']}%, turn p95 {m['latency_ms']['turn_p95']} ms.",
        "",
        "## 1. Hallucinated product facts inside 'resolved' answers",
        "",
        f"The deterministic grounding check (every number in a product-fact sentence "
        f"must appear in a KB document retrieved in that episode, or in what the client "
        f"said, or be a simple product/sum of those) flagged "
        f"{m['hallucination']['detected_in_final_answers']} of {m['episodes']} episodes "
        f"({m['hallucination']['detected_rate_pct']}%) with a product-fact claim in the "
        "final answer that no retrieved KB document supports. Console logs cannot see "
        "this at all: the tool calls succeeded, the run looked clean. Examples:",
        "",
    ]
    for ep_id, sc, sent in list(dict.fromkeys(ungrounded_examples))[:5]:
        lines.append(f"- `{ep_id}` ({sc}): \"{sent}\"")
    lines += ["",
              "Known blind spot: numbers that come from tool results other than KB "
              "search (ticket ages from `check_status`) are not in the evidence set, "
              "so the checker can flag them falsely. It also cannot see a wrong number "
              "that happens to appear somewhere in a retrieved doc. The earlier "
              "word-overlap version of this check flagged 26 of 100 baseline answers; "
              "spot checks against the dual judge showed most were correct answers "
              "(see the blog post). The judge layer is what exposed the checker."]
    lines += [
        "",
        "## 2. Tool-call failures and redundancy the success-rate number hid",
        "",
        f"{m['tools']['errors']} failing tool calls out of {m['tools']['total_calls']} "
        f"({m['tools']['error_rate_per_100']} per 100), kinds: "
        f"{json.dumps(m['tools']['error_kinds'])}; "
        f"{m['tools']['redundant_repeat_calls']} identical repeat calls "
        "(same tool, same args, same episode). First examples:",
        "",
    ]
    for c in tool_err_examples[:4]:
        lines.append(f"- `{c['tool']}` -> {c.get('error')}")
    lines += [
        "",
        "## 3. Escalation misses and spurious escalations",
        "",
        f"Policy says disputes, lockouts and legal questions go to a human. Baseline: "
        f"{m['escalation']['missed']} missed, {m['escalation']['spurious']} spurious. "
        f"Episodes that went off-KB with no retrieval at all: {len(no_kb)}.",
        "",
        "## 4. Judge scores on the baseline (5-criterion rubric)",
        "",
    ]
    if cal:
        lines.append(_md_table(
            [[crit, v] for crit, v in cal["judge_a_mean_scores"].items()],
            ["criterion", "mean score (1-5)"]))
        lines.append("")
        lines.append(_md_table(
            [[k, v["kappa3"], v["ac1_3"], v["agree3_pct"],
              "code only" if v.get("deterministic") else "LLM evidence + code"]
             for k, v in cal["dual_judge_kappa"].items()],
            ["criterion", "kappa (3-level)", "Gwet AC1 (3-level)", "raw agreement %",
             "scored from"]))
        lines.append("")
        lines.append(f"Target >= 0.85 met on kappa by: {cal['meets_085_target']['kappa3']}; "
                     f"on AC1 by: {cal['meets_085_target']['ac1_3']}. {cal.get('note', '')}")
        lines.append("")
        lines.append("Judge vs deterministic labels: " + json.dumps(
            cal["judge_vs_deterministic_kappa"]))
    else:
        lines.append("(eval pass not yet run for this directory)")
    lines.append("")
    lines.append("## 5. Latency breakdown (from traces)")
    lines.append("")
    lines.append(f"Turn p50 {m['latency_ms']['turn_p50']} ms / p95 "
                 f"{m['latency_ms']['turn_p95']} ms; KB searches per episode "
                 f"{m['tools']['kb_searches_per_episode']}. The trace spans attribute "
                 "latency to LLM rounds vs tool execution; redundant searches are "
                 "paid twice: once in tokens, once in wall clock.")
    return "\n".join(lines)


def delta_md(base_dir: Path, instr_dir: Path) -> str:
    b = json.load(open(base_dir / "metrics.json"))
    a = json.load(open(instr_dir / "metrics.json"))

    rows = [
        ["resolution rate (%)", b["resolution_rate"], a["resolution_rate"]],
        ["first-pass resolution (%)", b["first_pass_resolution"], a["first_pass_resolution"]],
        ["clarify-when-vague (%)", b["clarify_rate"], a["clarify_rate"]],
        ["injection blocked (%)", b["injection_blocked_rate"], a["injection_blocked_rate"]],
        ["hallucination detected in final answers (episodes)",
         b["hallucination"]["detected_in_final_answers"],
         a["hallucination"]["detected_in_final_answers"]],
        ["hallucination exposed to client (episodes)",
         b["hallucination"]["exposed_to_client"], a["hallucination"]["exposed_to_client"]],
        ["tool-calling errors per 100 calls", b["tools"]["error_rate_per_100"],
         a["tools"]["error_rate_per_100"]],
        ["redundant repeat tool calls", b["tools"]["redundant_repeat_calls"],
         a["tools"]["redundant_repeat_calls"]],
        ["KB searches per episode", b["tools"]["kb_searches_per_episode"],
         a["tools"]["kb_searches_per_episode"]],
        ["escalation: missed episodes", b["escalation"]["missed"],
         a["escalation"]["missed"]],
        ["escalation: spurious episodes", b["escalation"]["spurious"],
         a["escalation"]["spurious"]],
        ["turn latency p50 (ms)", b["latency_ms"]["turn_p50"], a["latency_ms"]["turn_p50"]],
        ["turn latency p95 (ms)", b["latency_ms"]["turn_p95"], a["latency_ms"]["turn_p95"]],
    ]
    lines = [
        "# Before / after: baseline vs instrumented re-run",
        "",
        "Same 50 personas, same seeded scenario deal, same model. v0: minimal prompt, "
        "guardrails observe-only. v1: policy prompt, enforced guardrails, tuned tool "
        "hints, full tracing + judge eval in the loop.",
        "",
        _md_table(rows, ["metric", "v0 baseline", "v1 instrumented"]),
        "",
        "## Outcome mix",
        "",
        _md_table([[k, b["outcome_counts"].get(k, 0), a["outcome_counts"].get(k, 0)]
                   for k in sorted(set(b["outcome_counts"]) | set(a["outcome_counts"]))],
                  ["outcome", "v0", "v1"]),
        "",
        "## Cost of the runs themselves",
        "",
        f"v0: {b['usage']['calls']} LLM calls, {b['usage']['in_tokens']}+"
        f"{b['usage']['out_tokens']} tokens, wall {b['wall_seconds']} s. "
        f"v1: {a['usage']['calls']} calls, {a['usage']['in_tokens']}+"
        f"{a['usage']['out_tokens']} tokens, wall {a['wall_seconds']} s.",
        "",
        "## By category (correct-episode rate %)",
        "",
    ]
    cats = sorted(set(b["by_category"]) | set(a["by_category"]))
    lines.append(_md_table(
        [[c, round(100 * b["by_category"].get(c, {}).get("correct", 0)
                   / max(1, b["by_category"].get(c, {}).get("episodes", 1)), 0),
          round(100 * a["by_category"].get(c, {}).get("correct", 0)
                / max(1, a["by_category"].get(c, {}).get("episodes", 1)), 0)] for c in cats],
        ["category", "v0 %", "v1 %"]))
    cb = _load(base_dir)["calibration"]
    ca = _load(instr_dir)["calibration"]
    if cb and ca:
        lines += [
            "",
            "## Judge scores (5-criterion rubric, judge A mean, 1-5)",
            "",
            _md_table([[k, cb["judge_a_mean_scores"][k], ca["judge_a_mean_scores"][k]]
                       for k in cb["judge_a_mean_scores"]],
                      ["criterion", "v0", "v1"]),
            "",
            "Dual-judge agreement, 3-level, kappa / AC1: v0 "
            + ", ".join(f"{k.split('_')[0]}={v['kappa3']}/{v['ac1_3']}"
                        for k, v in cb["dual_judge_kappa"].items())
            + "; v1 " + ", ".join(f"{k.split('_')[0]}={v['kappa3']}/{v['ac1_3']}"
                                 for k, v in ca["dual_judge_kappa"].items()) + ".",
        ]
    return "\n".join(lines)
