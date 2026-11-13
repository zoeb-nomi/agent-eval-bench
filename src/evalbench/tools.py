"""The 6 support-agent tools. Every tool returns {"ok": bool, ...} and records
its own execution latency; failures are data for the tool-error metric."""
from __future__ import annotations

import re
import time

from .kb import KB, TicketStore
from .llm import tool_schema

KB_TOOL = tool_schema(
    "search_kb",
    "Search the LedgerLane support knowledge base for policy and how-to information. "
    "Use before stating any product fact. Query should be a short natural phrase.",
    {"query": {"type": "string", "description": "search phrase, 3-8 words"}},
    ["query"],
)
CREATE_TOOL = tool_schema(
    "create_ticket",
    "Open a support ticket when the request needs a human action or follow-up. "
    "Requires a one-line subject.",
    {"subject": {"type": "string"}, "priority": {"type": "string",
     "enum": ["low", "normal", "high"], "description": "default normal"}},
    ["subject"],
)
ESCALATE_TOOL = tool_schema(
    "escalate",
    "Hand the conversation to a human specialist. Use for billing disputes, refund "
    "requests, account lockouts, legal or regulatory questions, or anything you are "
    "not sure about. Requires a reason.",
    {"ticket_id": {"type": "string", "description": "existing ticket id if there is one"},
     "reason": {"type": "string"}, "priority": {"type": "string",
     "enum": ["normal", "high", "urgent"]}},
    ["reason"],
)
STATUS_TOOL = tool_schema(
    "check_status",
    "Look up the current status of an existing support ticket by its id (TKT-XXXX).",
    {"ticket_id": {"type": "string"}},
    ["ticket_id"],
)
SUGGEST_TOOL = tool_schema(
    "suggest_resolution",
    "Get the ranked KB suggestions for a described problem, with doc ids, before "
    "writing the final answer. Use when the fix is a how-to.",
    {"problem": {"type": "string", "description": "one-line problem statement"}},
    ["problem"],
)
SUMMARISE_TOOL = tool_schema(
    "summarise",
    "Produce a structured summary of the conversation so far (issue, actions, next "
    "step). Use when closing an episode or handing over.",
    {"audience": {"type": "string", "enum": ["client", "human_agent"],
                  "description": "who the summary is for"}},
    ["audience"],
)

ALL_TOOLS = [KB_TOOL, CREATE_TOOL, ESCALATE_TOOL, STATUS_TOOL, SUGGEST_TOOL, SUMMARISE_TOOL]
TOOL_NAMES = {t["function"]["name"] for t in ALL_TOOLS}


class ToolBox:
    """Executes tools; logs every call for the metrics layer."""

    def __init__(self, kb: KB, tickets: TicketStore, transcript: list[dict] | None = None):
        self.kb = kb
        self.tickets = tickets
        self.events: list[dict] = []
        self.transcript = transcript if transcript is not None else []

    def _log(self, name: str, args: dict, result: dict, t0: float) -> dict:
        rec = {"tool": name, "args": args, "ok": bool(result.get("ok", True)),
               "error": result.get("error"), "ms": round((time.time() - t0) * 1000, 1)}
        self.events.append(rec)
        return result

    def log_error(self, name: str, error: str) -> None:
        """Record a client-side tool failure (parse/schema/unknown) as an event."""
        self.events.append({"tool": name, "args": {}, "ok": False, "error": error, "ms": 0.0})

    def execute(self, name: str, args: dict) -> dict:
        t0 = time.time()
        if name not in TOOL_NAMES:
            return self._log(name, args, {"ok": False,
                           "error": f"unknown tool {name!r}; valid: {sorted(TOOL_NAMES)}"}, t0)
        try:
            if name == "search_kb":
                q = str(args.get("query", "")).strip()
                if len(q) < 3:
                    return self._log(name, args, {"ok": False,
                                     "error": "query must be at least 3 characters"}, t0)
                hits = self.kb.search(q, top_k=3)
                return self._log(name, args, {"ok": True, "docs": hits}, t0)
            if name == "create_ticket":
                subject = str(args.get("subject", "")).strip()
                if not subject:
                    return self._log(name, args, {"ok": False, "error": "subject required"}, t0)
                priority = str(args.get("priority", "normal"))
                if priority not in ("low", "normal", "high"):
                    priority = "normal"
                return self._log(name, args, self.tickets.create(subject, priority), t0)
            if name == "escalate":
                reason = str(args.get("reason", "")).strip()
                if not reason:
                    return self._log(name, args, {"ok": False, "error": "reason required"}, t0)
                priority = str(args.get("priority", "high"))
                if priority not in ("normal", "high", "urgent"):
                    priority = "high"
                return self._log(name, args,
                                 self.tickets.escalate(args.get("ticket_id"), reason, priority), t0)
            if name == "check_status":
                t = self.tickets.get(str(args.get("ticket_id", "")))
                if not t:
                    return self._log(name, args, {"ok": False, "error": "ticket not found"}, t0)
                return self._log(name, args, {"ok": True,
                                 "ticket": {k: t[k] for k in ("id", "subject", "status",
                                                              "priority", "updated")}}, t0)
            if name == "suggest_resolution":
                problem = str(args.get("problem", "")).strip()
                if len(problem) < 5:
                    return self._log(name, args, {"ok": False, "error": "problem too short"}, t0)
                hits = self.kb.search(problem, top_k=2)
                steps = []
                for h in hits:
                    first = re.split(r"(?<=[.:])\s+", h["content"].strip())
                    steps.append({"doc": h["id"], "first_step": first[0]})
                return self._log(name, args, {"ok": True, "suggestions": steps}, t0)
            if name == "summarise":
                audience = args.get("audience", "client")
                if audience not in ("client", "human_agent"):
                    return self._log(name, args, {"ok": False,
                                     "error": "audience must be client or human_agent"}, t0)
                client_lines = [m["content"] for m in self.transcript if m.get("role") == "client"]
                agent_acts = [e for e in self.events if e["tool"] in
                              ("create_ticket", "escalate", "check_status")]
                summary = {
                    "audience": audience,
                    "issue": (client_lines[0][:160] if client_lines else "(no client text)"),
                    "turns": len(client_lines),
                    "actions": [f"{a['tool']}({'ok' if a['ok'] else 'error:' + str(a['error'])})"
                                for a in agent_acts],
                }
                return self._log(name, args, {"ok": True, "summary": summary}, t0)
            return self._log(name, args, {"ok": False, "error": "unreachable"}, t0)
        except Exception as e:  # tool crash is a tool error, not a crash of the run
            return self._log(name, args, {"ok": False, "error": f"tool crashed: {type(e).__name__}"}, t0)
