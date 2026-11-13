"""Offline smoke test: runs the full graph, harness and metrics with a scripted
stub LLM. No network, no keys. Verifies plumbing, not model quality."""
from __future__ import annotations

import json
import random

from .agent import SupportAgent
from .kb import KB, TicketStore
from .llm import Usage
from .metrics import compute_metrics
from .simulate import label_outcome
from .tracing import EpisodeTrace, FileTraceSink


class StubLLM:
    """Deterministic stand-in for ChatLLM: searches once, then answers from the
    tool result. Excercises tool-calling, guardrails and metric paths."""

    def __init__(self, *a, **k):
        self.model = "stub"
        self.last_usage = {}

    def chat(self, messages, tools=None, max_tokens=700, temperature=None):
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 10}
        last = messages[-1]
        if last["role"] == "tool":
            result = json.loads(last["content"])
            docs = result.get("docs") or []
            if docs:
                doc = docs[0]
                first_sent = doc["content"].strip().split(". ")[0]
                return {"role": "assistant", "content": f"{first_sent}. (Source: {doc['id']})",
                        "tool_calls": []}
            return {"role": "assistant", "content": "I could not verify that in the KB; "
                    "a specialist will confirm.", "tool_calls": []}
        q = "support policy"
        return {"role": "assistant", "content": "",
                "tool_calls": [{"id": "call_1", "type": "function",
                                "function": {"name": "search_kb",
                                             "arguments": json.dumps({"query": q})}}]}


def run() -> int:
    kb = KB()
    import yaml
    from . import config
    scenarios = yaml.safe_load(open(config.DATA_DIR / "scenarios.yaml"))
    personas = yaml.safe_load(open(config.DATA_DIR / "personas.yaml"))["personas"]

    sink = FileTraceSink(config.REPO_ROOT / "tests" / "smoke_traces.jsonl")
    usage = Usage()
    agent = SupportAgent("v1", kb, usage, llm_override=StubLLM())

    ok = True

    # one episode per scenario kind, all offline
    eps = []
    for i, sc in enumerate(scenarios):
        persona = personas[i % len(personas)]
        trace = EpisodeTrace(sink, f"smoke-{sc['id']}", {"scenario": sc["id"]})
        from .guardrails import Guardrails
        from .tools import ToolBox
        ctx = {"guardrails": Guardrails(kb, enforce=True), "toolbox": ToolBox(kb, TicketStore()),
               "trace": trace, "retrieved": []}
        turns = []
        history = []
        client_msg = sc["text"].replace("{n_gstins}", "2").replace("{ret}", "GSTR-1") \
            .replace("{period}", "September").replace("{code}", "1005") \
            .replace("{hours}", "19").replace("{ticket_id}", "TKT-1042")
        for t in range(3):
            if client_msg is None:
                break
            turn = agent.run_turn(ctx, history, client_msg)
            history.append({"role": "client", "content": client_msg})
            history.append({"role": "agent", "content": turn["agent"]})
            turns.append(turn)
            client_msg = None
        outcome = label_outcome(turns, ctx["guardrails"].events, sc)
        eps.append({"outcome": outcome, "turns": turns, "expected": sc["expected"],
                    "scenario_id": sc["id"], "scenario_category": sc["category"]})
        # every turn must have produced some agent text
        if not all(t["agent"] for t in turns):
            print(f"FAIL: empty agent text in {sc['id']}")
            ok = False
        trace.close(outcome)

    m = compute_metrics([{"outcome": e["outcome"], "turns": e["turns"],
                          "expected": e["expected"],
                          "scenario_category": e["scenario_category"]} for e in eps], "smoke")
    if m["episodes"] != len(scenarios):
        print("FAIL: episode count mismatch")
        ok = False
    if not (m["tools"]["total_calls"] > 0):
        print("FAIL: no tool calls recorded")
        ok = False
    sink.close()
    (config.REPO_ROOT / "tests" / "smoke_traces.jsonl").unlink(missing_ok=True)
    print("smoke ok" if ok else "smoke FAILED")
    return 0 if ok else 1
