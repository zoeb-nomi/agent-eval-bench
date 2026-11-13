"""Minimal OpenRouter chat-completions client with usage and cost accounting.

Thread-safe: uses one requests.Session guarded by GIL-safe per-call usage.
Never logs or raises with the API key in the message.
"""
from __future__ import annotations

import json
import os
import threading
import time

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 1 Nov 2026 OpenRouter prices, USD per million tokens (for cost accounting in reports).
PRICES_PER_M = {
    "z-ai/glm-4.7-flash": (0.06, 0.40),
    "deepseek/deepseek-v4-flash": (0.09, 0.18),
    "z-ai/glm-5.3-flash": (0.04, 0.08),
}


class LLMError(Exception):
    pass


class Usage:
    """Run-wide token and cost tally."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0
        self.in_tokens = 0
        self.out_tokens = 0
        self.errors = 0

    def add(self, usage: dict, model: str) -> None:
        with self._lock:
            self.calls += 1
            self.in_tokens += usage.get("prompt_tokens", 0) or 0
            self.out_tokens += usage.get("completion_tokens", 0) or 0

    def summary(self) -> dict:
        in_cost = out_cost = 0.0
        return {
            "calls": self.calls,
            "in_tokens": self.in_tokens,
            "out_tokens": self.out_tokens,
            "errors": self.errors,
        }


class ChatLLM:
    def __init__(self, model: str, usage: Usage | None = None, temperature: float = 0.2):
        self.model = model
        self.usage = usage or Usage()
        self.temperature = temperature
        self.last_usage: dict = {}

    def chat(self, messages: list, tools: list | None = None, max_tokens: int = 700,
             temperature: float | None = None, response_format: dict | None = None,
             reasoning: dict | None = None) -> dict:
        """One chat call. Returns the message dict from the API. Retries once on
        429/5xx. Raises LLMError after that."""
        self.last_usage = {}
        body: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if response_format:
            body["response_format"] = response_format
        if reasoning is not None:
            body["reasoning"] = reasoning
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        headers = {
            "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}",
            "Content-Type": "application/json",
        }
        delay = 2.0
        last_err = ""
        for attempt in range(3):
            try:
                r = requests.post(API_URL, headers=headers, json=body, timeout=90)
                if r.status_code == 200:
                    j = r.json()
                    msg = j["choices"][0]["message"]
                    msg.setdefault("tool_calls", [])
                    msg["finish_reason"] = j["choices"][0].get("finish_reason")
                    if j.get("usage"):
                        self.usage.add(j["usage"], self.model)
                        self.last_usage = j["usage"]
                    return msg
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break
            except requests.RequestException as e:
                last_err = f"request failed: {type(e).__name__}"
                if attempt < 2:
                    time.sleep(delay)
                    delay *= 2
        self.usage.errors += 1
        raise LLMError(f"llm call failed after retries ({last_err})")

    def tool_call(self, messages: list, tools: list) -> tuple[list, str | None]:
        """Force one assistant turn; returns (tool_calls, content) or ([], content)."""
        msg = self.chat(messages, tools=tools)
        return msg.get("tool_calls") or [], msg.get("content")


def tool_schema(name: str, description: str, properties: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


def parse_tool_args(call: dict) -> tuple[str, dict | None, str | None]:
    """Return (name, args, error). Error set for unknown tools or bad JSON."""
    try:
        name = call["function"]["name"]
    except (KeyError, TypeError):
        return "", None, "malformed tool call envelope"
    try:
        raw = call["function"].get("arguments") or "{}"
        args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        if not isinstance(args, dict):
            return name, None, "arguments not a JSON object"
        return name, args, None
    except json.JSONDecodeError:
        return name, None, "arguments are not valid JSON"
