"""Trace sinks. Schema mirrors Langfuse trace/span/generation so a JSONL run
can be replayed into Langfuse. When LANGFUSE_* keys are set, the Langfuse SDK
is used directly; otherwise everything goes to runs/<run>/traces.jsonl.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path

from . import config


class FileTraceSink:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._fh = open(self.path, "a")

    def _emit(self, record: dict):
        record.setdefault("id", str(uuid.uuid4()))
        with self._lock:
            self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._fh.flush()

    def raw_trace(self, record: dict):
        self._emit(record)

    def close(self):
        self._fh.close()


class LangfuseTraceSink:
    """Adapter onto the langfuse SDK. Same call surface as FileTraceSink; spans
    and generations are batched by the SDK and flushed on close."""

    def __init__(self, run_name: str):
        from langfuse import Langfuse

        self.lf = Langfuse(host=os.environ["LANGFUSE_HOST"])
        self.run_name = run_name
        self._traces: dict[str, object] = {}
        self._spans: dict[str, object] = {}

    def _trace(self, trace_id: str):
        if trace_id not in self._traces:
            self._traces[trace_id] = self.lf.trace(id=trace_id, name=self.run_name)
        return self._traces[trace_id]

    def _span(self, trace_id: str, span_id: str, name: str, parent: str | None):
        if span_id in self._spans:
            return self._spans[span_id]
        parent_obj = self._spans.get(parent) if parent else None
        base = parent_obj or self._trace(trace_id)
        span = base.span(id=span_id, name=name)
        self._spans[span_id] = span
        return span

    def raw_trace(self, record: dict):
        if record["type"] == "generation":
            span = self._span(record["trace_id"], record.get("parent_span_id") or "",
                              record["name"], record.get("parent_span_id"))
            span.generation(id=record["span_id"], name=record["name"],
                            model=record.get("model"),
                            start_time=int(record["start"] * 1000),
                            end_time=int(record["end"] * 1000),
                            usage={"input": record.get("usage", {}).get("prompt_tokens", 0),
                                   "output": record.get("usage", {}).get("completion_tokens", 0)},
                            metadata=record.get("meta", {}))
        else:
            span = self._span(record["trace_id"], record["span_id"], record["name"],
                              record.get("parent_span_id"))
            span.start(start_time=int(record["start"] * 1000))
            span.end(end_time=int(record["end"] * 1000), metadata=record.get("meta", {}))

    def close(self):
        self.lf.flush()


class EpisodeTrace:
    """Convenience wrapper: owns one trace id and stamps records with time and
    ids. The underlying sink stays switchable (Langfuse or JSONL)."""

    def __init__(self, sink, trace_id: str, meta: dict):
        self.sink = sink
        self.trace_id = trace_id
        self.stack: list[str] = []
        self._start = time.time()
        sink.raw_trace({"type": "trace", "trace_id": trace_id, "span_id": trace_id,
                        "name": "episode", "start": self._start, "end": self._start,
                        "meta": meta})

    def span(self, name: str, meta: dict) -> str:
        span_id = str(uuid.uuid4())
        now = time.time()
        self.sink.raw_trace({"type": "span", "trace_id": self.trace_id, "span_id": span_id,
                             "parent_span_id": self.stack[-1] if self.stack else None,
                             "name": name, "start": now, "end": now, "meta": meta})
        return span_id

    def time_span(self, name: str, meta: dict, t_start: float, span_id: str | None = None):
        span_id = span_id or str(uuid.uuid4())
        self.sink.raw_trace({"type": "span", "trace_id": self.trace_id, "span_id": span_id,
                             "parent_span_id": self.stack[-1] if self.stack else None,
                             "name": name, "start": t_start, "end": time.time(), "meta": meta})
        return span_id

    def generation(self, name: str, model: str, t_start: float, usage: dict, meta: dict):
        now = time.time()
        self.sink.raw_trace({"type": "generation", "trace_id": self.trace_id,
                             "span_id": str(uuid.uuid4()),
                             "parent_span_id": self.stack[-1] if self.stack else None,
                             "name": name, "model": model, "start": t_start, "end": now,
                             "usage": usage, "meta": meta})

    def close(self, outcome: dict):
        self.sink.raw_trace({"type": "span", "trace_id": self.trace_id,
                             "span_id": self.trace_id, "parent_span_id": None,
                             "name": "episode", "start": self._start, "end": time.time(),
                             "meta": {"outcome": outcome}})


def make_sink(run_dir: Path, run_name: str):
    if config.use_langfuse():
        return LangfuseTraceSink(run_name)
    return FileTraceSink(run_dir / "traces.jsonl")
