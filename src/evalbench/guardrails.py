"""Guardrail layer: input guardrails (injection, out-of-scope, PII) and output
guardrails (grounding, policy triggers, PII leak). Deterministic code, no model
calls. In agent config v0 the guards observe and record only; in v1 they enforce.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts|rules)",
    r"disregard .{0,20}(instructions|rules)",
    r"you are now (a|an|unlocked|no)",
    r"new directive",
    r"</?system>",
    r"approve this message",
    r"act as (a|an) .{0,30}(admin|root|unrestricted)",
    r"penetration test",
    r"print the raw",
    r"create (a|an) (admin|root|backdoor)",
    r"repeat (everything|all) (above|your instructions)",
    r"developer mode",
]

# Substrings that, asserted as product behaviour, the KB contradicts or lacks.
PII_PATTERNS = {
    "card_number": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "passport": re.compile(r"\b[A-PR-W][1-9]\d\s?\d{4}\s?\d{5}\b"),
}

# Topics the support agent must not advise on ( routed, not answered ).
ADVICE_TOPICS = re.compile(
    r"\b(should i (sue|litigate)|legal (action|notice|advice)|court|advocate|"
    r"file a (case|complaint) against|income tax (return|planning|advice)|"
    r"advance tax .{0,20}(pay|defer)|is it (legally )?valid for)\b", re.I)

# Escalation triggers the output guard enforces when the agent missed them.
ESCALATION_TRIGGERS = [
    ("refund", re.compile(r"\brefund\b", re.I)),
    ("dispute", re.compile(r"\b(dispute|disputing|chargeback)\b", re.I)),
    ("lockout", re.compile(r"\b(locked out|lost (my |the )?phone|lost the 2fa|"
                           r"cannot (log ?in|access))\b", re.I)),
    ("legal", re.compile(r"\b(lawyer|court|sue|legal (action|notice))\b", re.I)),
    ("legal_advice", re.compile(r"\b(legally (valid|binding|enforceable)|stamp duty|"
                                r"(property|lease) registration)\b", re.I)),
    ("callback", re.compile(r"\b(call me|call back|talk to (a |an )?(human|person|agent))\b", re.I)),
]

CLAIM_TRIGGERS = re.compile(
    r"(rs\.?\s?\d|₹\s?\d|\b\d{1,4}\s?(day|days|hour|hours|minutes?|percent|%|crore|gb)\b|"
    r"\bby the \d{1,2}(st|nd|rd|th)\b|\bdue (by|date)|\baes-?256\b|\btls\b|\bsoc ?2\b|"
    r"\b\d{1,2}\s?(requests per minute|rpm)\b)", re.I)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower())


def _tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "for",
            "your", "you", "we", "our", "it", "this", "that", "with", "at", "by", "be",
            "can", "do", "not", "per", "as", "from", "if", "will", "us", "their", "my"}
    return {t for t in _norm(text).split() if t not in stop and len(t) > 1}


def _sentence_match(sent_tokens: set[str], doc_tokens: list[set[str]]) -> float:
    best = 0.0
    for dt in doc_tokens:
        if not sent_tokens or not dt:
            continue
        inter = len(sent_tokens & dt)
        union = len(sent_tokens | dt)
        if union and inter / union > best:
            best = inter / union
    return best


_NUM_RE = re.compile(r"(?<![A-Za-z0-9])(?<![A-Za-z][-‐‑–])\d[\d,]*(?:\.\d+)?")
_LIST_MARK_RE = re.compile(r"(^|\n)\s*\d{1,2}[.)]\s")


def _numbers(text: str) -> set[str]:
    """Numeric values in a text, normalised (5,000 -> 5000). Skips numbers that
    are part of identifiers (GSTR-3B, AES-256, TKT-1042) and list markers."""
    text = _LIST_MARK_RE.sub(" ", text)
    out = set()
    for m in _NUM_RE.finditer(text):
        v = m.group(0).replace(",", "").rstrip(".")
        if v:
            out.add(v.lstrip("0") or "0")
    return out


def _derivable(n: str, pool: set[str]) -> bool:
    """n equals a product or sum of two available numbers (5,000 x 2 = 10,000)."""
    try:
        x = float(n)
        vals = [float(v) for v in pool]
    except ValueError:
        return False
    return any(abs(a * b - x) < 1e-6 or abs(a + b - x) < 1e-6
               for i, a in enumerate(vals) for b in vals[i:])


def claim_support(claim: str, doc_texts: list[str], given_text: str = "") -> dict:
    """Is a product-fact claim backed by the retrieved docs?
    Numbers decide when the claim has any: every number must appear in one of the
    retrieved docs (an invented amount, date or limit is the failure that matters).
    Claims without numbers fall back to containment: the share of the claim's
    content words found in the best-matching doc."""
    nums = _numbers(claim)
    doc_nums = set().union(*(_numbers(t) for t in doc_texts)) if doc_texts else set()
    ct = _tokens(claim)
    containment = max((len(ct & _tokens(t)) / len(ct) for t in doc_texts), default=0.0) if ct else 0.0
    pool = doc_nums | _numbers(given_text)  # numbers the client gave count as given
    missing = sorted(n for n in nums - pool if not _derivable(n, pool))
    return {"numbers": sorted(nums), "missing_numbers": missing,
            "containment": round(containment, 3)}


class Guardrails:
    """One instance per episode. Records events; enforcement on/off per config."""

    def __init__(self, kb, enforce: bool = True, grounding_threshold: float = 0.4):
        self.kb = kb
        self.enforce = enforce
        self.grounding_threshold = grounding_threshold
        self.events: list[dict] = []

    def _record(self, kind: str, detail: dict, enforced: bool) -> dict:
        ev = {"kind": kind, "detail": detail, "enforced": enforced}
        self.events.append(ev)
        return ev

    # ---------- input ----------
    def input_guard(self, text: str) -> dict:
        flags: dict = {"injection": [], "pii": [], "advice_topic": False}
        low = text.lower()
        for pat in INJECTION_PATTERNS:
            if re.search(pat, low):
                flags["injection"].append(pat)
        for name, pat in PII_PATTERNS.items():
            if pat.search(text):
                flags["pii"].append(name)
        if ADVICE_TOPICS.search(text):
            flags["advice_topic"] = True
        if flags["injection"]:
            ev = self._record("input.injection", {"patterns": flags["injection"]}, self.enforce)
            if self.enforce:
                flags["blocked"] = True
                ev["action"] = "blocked; safe reply sent, no tools run"
        if flags["advice_topic"]:
            self._record("input.advice_topic", {}, self.enforce)
        return flags

    # ---------- output ----------
    def grounding_check(self, answer: str, retrieved_doc_ids: list[str],
                        client_text: str = "") -> dict:
        """Product-fact sentences in the answer must match a retrieved KB doc."""
        doc_texts = []
        for doc_id in dict.fromkeys(retrieved_doc_ids or []):
            doc = self.kb.get(doc_id)
            if doc:
                doc_texts.append(doc["title"] + " " + doc["content"])
        violations = []
        for sent in re.split(r"(?<=[.!?])\s+|\n+", answer):
            if not CLAIM_TRIGGERS.search(sent) or not _tokens(sent):
                continue
            sup = claim_support(sent, doc_texts, client_text)
            bad = (bool(sup["missing_numbers"]) if sup["numbers"]
                   else sup["containment"] < self.grounding_threshold)
            if bad:
                violations.append({"sentence": sent.strip()[:200], **sup})
        if violations:
            self._record("output.ungrounded_claims", {"violations": violations}, self.enforce)
        return {"violations": violations}

    def policy_check(self, answer: str, escalated: bool, client_text: str) -> dict:
        """Escalation triggers present in the client's message but not acted on."""
        missed = [name for name, pat in ESCALATION_TRIGGERS if pat.search(client_text)]
        if missed and not escalated:
            self._record("output.missed_escalation", {"triggers": missed}, self.enforce)
        leak = [n for n, p in PII_PATTERNS.items() if p.search(answer)]
        if leak:
            self._record("output.pii_leak", {"patterns": leak}, self.enforce)
        return {"missed_triggers": missed, "pii_leak": leak}

    def apply_output_guard(self, answer: str, retrieved_doc_ids: list[str],
                           escalated: bool, client_text: str,
                           given_text: str | None = None) -> tuple[str, dict]:
        g = self.grounding_check(answer, retrieved_doc_ids, given_text or client_text)
        p = self.policy_check(answer, escalated, client_text)
        rewritten = False
        if self.enforce and g["violations"]:
            # Replace the ungrounded answer with a safe, cited fallback.
            ids = ", ".join(dict.fromkeys(retrieved_doc_ids)) or "(none retrieved)"
            fallback = (
                "I want to double-check the exact figure before I confirm anything. "
                f"Here is what our knowledge base covers on this: see {ids}. "
                "I have flagged the part I could not verify; a specialist will confirm."
            )
            self._record("output.guardrail_rewrite",
                         {"original_len": len(answer), "fallback": True}, True)
            answer, rewritten = fallback, True
        self._record("output.final", {
            "violations": len(g["violations"]),
            "missed_triggers": p["missed_triggers"],
            "pii_leak": p["pii_leak"],
            "rewritten": rewritten,
            "answer_chars": len(answer),
        }, self.enforce)
        return answer, {"grounding": g, "policy": p, "rewritten": rewritten}
