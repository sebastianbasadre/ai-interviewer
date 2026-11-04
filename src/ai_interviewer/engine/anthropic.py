"""Bounded Anthropic JSON requests; no requests on import or construction.

The provider receives filtered professional text prepared by the analyzer or scorer.
The application does not add candidate profile metadata, microphone data or answers
from other interviews. Text filtering is conservative, not guaranteed anonymization.
"""
from __future__ import annotations

import asyncio
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from threading import Lock

from pydantic import SecretStr

from .llm import AnswerAnalysis

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
MAX_OUTPUT_TOKENS = 512


class ConversationModelError(Exception):
    """Diagnostics never contain provider bodies, candidate content or credentials."""


class CallBudget:
    """One shared persistent limit across interviews, reconnections and restarts."""

    def __init__(self, path: Path, limit: int):
        self.path, self.limit = Path(path), limit

    def reserve(self, count: int = 1):
        if type(count) is not int or count < 1:
            raise ConversationModelError("Invalid call reservation.")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ConversationModelError("Invalid conversation budget storage.")
        # Short write transaction also protects concurrent processes. Reserve before
        # the request; failed/timed-out requests are conservatively charged as calls.
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY, calls INTEGER NOT NULL)")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT calls FROM budget WHERE id=1").fetchone()
            used = row[0] if row else 0
            if used + count > self.limit:
                raise ConversationModelError("Conversation call limit reached.")
            db.execute("INSERT OR REPLACE INTO budget VALUES(1, ?)", (used + count,))
        self.path.chmod(0o600)


class ReservedCalls:
    """Consume an already persisted reservation; failures do not refund its quota."""
    def __init__(self, count: int):
        self.remaining = count
        self._lock = Lock()

    def reserve(self):
        with self._lock:
            if self.remaining <= 0:
                raise ConversationModelError("Reserved call limit reached.")
            self.remaining -= 1


class AnthropicJSONModel:
    max_input_chars = 8000
    max_input_bytes = 24000
    max_output_tokens = MAX_OUTPUT_TOKENS
    max_response_bytes = 65536
    effort = "low"

    def __init__(self, api_key: SecretStr, *, model: str, budget: CallBudget | ReservedCalls,
                 timeout_seconds: float = 8, transport=None):
        if not api_key.get_secret_value().strip():
            raise ConversationModelError("ANTHROPIC_API_KEY is required.")
        self._api_key = api_key
        self.model, self.budget = model, budget
        self.timeout_seconds, self._transport = timeout_seconds, transport

    async def complete(self, system: str, user: str) -> str:
        import httpx
        if len(system) + len(user) > self.max_input_chars or len((system + user).encode()) > self.max_input_bytes:
            raise ConversationModelError("Conversation input exceeds its limit.")
        schema = self.output_schema()
        payload = {
            "model": self.model, "max_tokens": self.max_output_tokens,
            "system": system, "messages": [{"role": "user", "content": user}],
            "output_config": {"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
        }
        try:
            await asyncio.to_thread(self.budget.reserve)
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False,
                                         trust_env=False, transport=self._transport) as client:
                response = await client.post(MESSAGES_URL, json=payload, headers={
                    "Authorization": "Bearer " + self._api_key.get_secret_value(),
                    "anthropic-version": API_VERSION,
                })
                if response.status_code != 200:
                    raise ConversationModelError("Conversation provider unavailable.")
                if len(response.content) > self.max_response_bytes:
                    raise ConversationModelError("Conversation response exceeds its limit.")
                data = response.json()
            if data.get("stop_reason") != "end_turn" or (data.get("stop_details") or {}).get("type") == "refusal":
                raise ConversationModelError("Conversation provider did not complete classification.")
            blocks = data.get("content", [])
            texts = [b["text"] for b in blocks if b.get("type") == "text"]
            if len(texts) != 1:
                raise ConversationModelError("Invalid conversation response.")
            result = json.loads(texts[0])
            if set(result) != set(schema["required"]):
                raise ConversationModelError("Incomplete conversation response.")
            return self.validate_result(result)
        except ConversationModelError:
            raise
        except Exception:
            raise ConversationModelError("Conversation provider failed.") from None

    def output_schema(self) -> dict:
        raise NotImplementedError

    def validate_result(self, result) -> str:
        raise NotImplementedError


class AnthropicAnswerModel(AnthropicJSONModel):
    def output_schema(self):
        schema = AnswerAnalysis.model_json_schema()
        schema["required"] = list(schema["properties"])
        for value in schema["properties"].values():
            value.pop("default", None)
        return schema

    def validate_result(self, result):
        return AnswerAnalysis.model_validate(result, strict=True).model_dump_json()
