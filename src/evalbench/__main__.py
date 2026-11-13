"""CLI: python -m evalbench <simulate|evaluate|report|smoke> [options]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config


def main(argv=None):
    p = argparse.ArgumentParser(prog="evalbench")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_sim = sub.add_parser("simulate", help="run the 50-persona simulation")
    s_sim.add_argument("--version", choices=["v0", "v1"], default="v1")
    s_sim.add_argument("--out", default=None, help="run dir (default runs/<version>)")
    s_sim.add_argument("--label", default="")

    s_eval = sub.add_parser("evaluate", help="judge eval + calibration on a run dir")
    s_eval.add_argument("--run", required=True)
    s_eval.add_argument("--judge", choices=["a", "b", "both", "cal"], default="both")

    s_rep = sub.add_parser("report", help="write findings.md and delta.md")
    s_rep.add_argument("--baseline", required=True)
    s_rep.add_argument("--instrumented", required=True)

    sub.add_parser("smoke", help="offline smoke test with a stub LLM")

    args = p.parse_args(argv)

    if args.cmd == "simulate":
        from .simulate import run_simulation
        out = Path(args.out or ("runs/" + ("baseline_v0" if args.version == "v0"
                                           else "instrumented_v1")))
        m = run_simulation(out, args.version, label=args.label)
        print(json_summary(m))
    elif args.cmd == "evaluate":
        from .judge import evaluate_run
        cal = evaluate_run(Path(args.run), which=args.judge)
        print(cal and __import__("json").dumps(cal, indent=2))
    elif args.cmd == "report":
        from .report import delta_md, findings_md
        base, instr = Path(args.baseline), Path(args.instrumented)
        rep = config.PKG_ROOT.parent.parent / "reports"
        rep.mkdir(exist_ok=True)
        (rep / "findings.md").write_text(findings_md(base))
        (rep / "delta.md").write_text(delta_md(base, instr))
        print(f"wrote {rep / 'findings.md'} and {rep / 'delta.md'}")
    elif args.cmd == "smoke":
        from .smoke import run
        sys.exit(run())


def json_summary(m: dict) -> str:
    import json
    return json.dumps({k: m[k] for k in
                       ("label", "resolution_rate", "first_pass_resolution",
                        "injection_blocked_rate", "turn_p95" if "turn_p95" in m else
                        "latency_ms", "tools", "hallucination", "escalation",
                        "usage", "wall_seconds")}, indent=2, default=str)


if __name__ == "__main__":
    main()
