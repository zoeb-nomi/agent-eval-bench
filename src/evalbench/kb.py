"""Knowledge base over synthetic LedgerLane support docs, plus ticket store."""
from __future__ import annotations

import re
import threading
import time
import uuid
from pathlib import Path

import yaml

from . import config


def _norm_tokens(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9%.,:/-]+", " ", text)
    stop = {"the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "for",
            "your", "you", "we", "our", "it", "this", "that", "with", "at", "by", "be",
            "can", "do", "does", "not", "per", "as", "from", "if", "so", "my", "us",
            "under", "their", "its", "has", "have", "will", "up", "than", "then"}
    toks = [t for t in text.split() if t and t not in stop and not all(c in ".,:/" for c in t)]
    return toks


class KB:
    def __init__(self) -> None:
        with open(config.DATA_DIR / "kb_docs.yaml") as f:
            self.docs: list[dict] = yaml.safe_load(f)
        self.by_id = {d["id"]: d for d in self.docs}

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        q = _norm_tokens(query)
        if not q:
            return []
        scored = []
        for d in self.docs:
            body = _norm_tokens(d["title"] + " " + d["content"] + " " + d["category"].replace("-", " "))
            qs = set(q)
            overlap = len(qs & set(body))
            # phrase bonus: doc sentences containing a rare query token score higher
            rare = [t for t in qs if len(t) > 6]
            bonus = sum(3 for t in rare if t in set(body))
            cat = 2 if d["category"].replace("-", " ").split()[0] in qs else 0
            scored.append((overlap + bonus + cat, d["id"]))
        scored.sort(reverse=True)
        out = []
        for score, doc_id in scored[:top_k]:
            if score <= 0:
                break
            d = self.by_id[doc_id]
            out.append({"id": d["id"], "title": d["title"], "category": d["category"],
                        "content": d["content"]})
        return out

    def get(self, doc_id: str) -> dict | None:
        return self.by_id.get(doc_id)


class TicketStore:
    """In-memory ticket store; persisted to JSON at run end."""

    STATUSES = ("open", "in_progress", "waiting_on_client", "resolved", "escalated")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.tickets: dict[str, dict] = {}
        self._seed_demo_tickets()

    def _seed_demo_tickets(self) -> None:
        now = time.time()
        for tid, subject, status in [
            ("TKT-1042", "E-invoice IRP rejections on 3 invoices", "in_progress"),
            ("TKT-0871", "GSTR-2B reconciliation missing supplier invoices", "waiting_on_client"),
            ("TKT-0903", "Export contract vault as signed zip", "resolved"),
        ]:
            self.tickets[tid] = {"id": tid, "subject": subject, "status": status,
                                 "created": now - 86400 * (3 if status != "resolved" else 10),
                                 "updated": now - 3600, "priority": "normal",
                                 "events": [{"t": "created"}, {"t": "routed to product support"}]}

    def create(self, subject: str, priority: str = "normal", category: str = "general") -> dict:
        with self._lock:
            tid = f"TKT-{uuid.uuid4().int % 10**4:04d}"
            t = {"id": tid, "subject": subject[:120], "status": "open", "priority": priority,
                 "category": category, "created": time.time(), "updated": time.time(),
                 "events": [{"t": "created"}]}
            self.tickets[tid] = t
            return {"ok": True, "ticket": t}

    def get(self, ticket_id: str) -> dict | None:
        with self._lock:
            return self.tickets.get((ticket_id or "").strip().upper())

    def escalate(self, ticket_id: str | None, reason: str, priority: str) -> dict:
        with self._lock:
            if ticket_id:
                t = self.tickets.get(ticket_id.strip().upper())
            else:
                tid = f"TKT-{uuid.uuid4().int % 10**4:04d}"
                t = self.tickets.setdefault(tid, {"id": tid, "subject": "(auto)",
                                                  "created": time.time(), "updated": time.time(),
                                                  "events": []})
            if not t:
                return {"ok": False, "error": f"unknown ticket {ticket_id}"}
            t["status"] = "escalated"
            t["priority"] = priority or "high"
            t["updated"] = time.time()
            t["events"].append({"t": f"escalated: {reason[:160]}"})
            return {"ok": True, "ticket": t}

    def update_status(self, ticket_id: str, status: str) -> dict:
        with self._lock:
            t = self.tickets.get((ticket_id or "").strip().upper())
            if not t:
                return {"ok": False, "error": f"unknown ticket {ticket_id}"}
            if status not in self.STATUSES:
                return {"ok": False, "error": f"status must be one of {self.STATUSES}"}
            t["status"] = status
            t["updated"] = time.time()
            t["events"].append({"t": f"status -> {status}"})
            return {"ok": True, "ticket": t}
