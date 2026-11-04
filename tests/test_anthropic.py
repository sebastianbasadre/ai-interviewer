import json
from concurrent.futures import ThreadPoolExecutor

import httpx
from pydantic import SecretStr
import pytest

from ai_interviewer.engine.anthropic import (
    API_VERSION, MAX_OUTPUT_TOKENS, MESSAGES_URL,
    AnthropicAnswerModel, CallBudget, ConversationModelError,
)
from ai_interviewer.engine.llm import AnswerAnalysis


def reply(**changes):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text":
            AnswerAnalysis(concrete_example=True).model_dump_json()}], **changes}


def model(tmp_path, handler, limit=2):
    return AnthropicAnswerModel(SecretStr("private-test-key"), model="claude-haiku-5-5",
        budget=CallBudget(tmp_path / "budget.sqlite3", limit), transport=httpx.MockTransport(handler))


async def test_provider_uses_bounded_schema_and_no_automatic_retry(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        assert str(request.url) == MESSAGES_URL
        assert request.headers["Authorization"] == "Bearer private-test-key"
        assert request.headers["anthropic-version"] == API_VERSION
        data = json.loads(request.content)
        assert data["max_tokens"] == MAX_OUTPUT_TOKENS
        assert data["messages"] == [{"role": "user", "content": "Synthetic professional content"}]
        schema = data["output_config"]["format"]["schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(AnswerAnalysis.model_fields)
        return httpx.Response(200, json=reply())
    provider = model(tmp_path, handler, limit=1)
    assert json.loads(await provider.complete("System", "Synthetic professional content"))["concrete_example"]
    with pytest.raises(ConversationModelError, match="limit"):
        await provider.complete("System", "Another answer")
    assert len(calls) == 1


@pytest.mark.parametrize("status,data", [
    (401, {"error": "private-test-key candidate-secret"}),
    (429, {}), (503, {}), (307, {}),
    (200, reply(stop_reason="max_tokens")),
    (200, reply(stop_details={"type": "refusal"})),
    (200, reply(content=[{"type": "text", "text": "candidate-secret"}])),
    (200, reply(content=[{"type": "text", "text": '{"concrete_example":true}'}])),
    (200, reply(content=[{"type": "text", "text": AnswerAnalysis().model_dump_json().replace('false', '"false"')} ])),
])
async def test_provider_failures_do_not_leak_body_or_retry(tmp_path, status, data):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json=data, headers={"Location": "https://other.invalid"})
    provider = model(tmp_path, handler)
    with pytest.raises(ConversationModelError) as error:
        await provider.complete("System", "candidate-secret")
    assert "candidate-secret" not in str(error.value)
    assert "private-test-key" not in str(error.value)
    assert len(calls) == 1


async def test_provider_timeout_is_safe_and_charges_reserved_attempt(tmp_path):
    def handler(request):
        raise httpx.ReadTimeout("private-test-key candidate-secret", request=request)
    provider = model(tmp_path, handler, limit=1)
    with pytest.raises(ConversationModelError, match="failed"):
        await provider.complete("System", "Answer")
    with pytest.raises(ConversationModelError, match="limit"):
        await provider.complete("System", "Answer")


async def test_input_cap_prevents_network_and_budget_reservation(tmp_path):
    calls = []
    provider = model(tmp_path, lambda request: calls.append(request))
    with pytest.raises(ConversationModelError, match="input"):
        await provider.complete("System", "a" * 8001)
    assert not calls and not provider.budget.path.exists()


def test_budget_survives_new_instances_and_serializes_concurrent_reservations(tmp_path):
    path = tmp_path / "budget.sqlite3"
    def reserve(_):
        try:
            CallBudget(path, 3).reserve()
            return True
        except ConversationModelError:
            return False
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(reserve, range(8))) == 3
    with pytest.raises(ConversationModelError, match="limit"):
        CallBudget(path, 3).reserve()
