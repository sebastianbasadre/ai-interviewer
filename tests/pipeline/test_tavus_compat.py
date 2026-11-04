"""Provider-boundary tests use doubles; the optional SDK tests never contact Tavus."""
from copy import deepcopy

import pytest

from ai_interviewer.config import Settings
from ai_interviewer.pipeline.tavus_compat import (
    TAVUS_BASE_URL, TavusCompatibilityError, TavusSessionAdapter, create_tavus_video_service,
)


class Response:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    async def json(self):
        return deepcopy(self.body)


class Context:
    def __init__(self, response):
        self.response = response
        self.closed = False

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, *args):
        self.closed = True


class Session:
    def __init__(self):
        self.calls = []
        self.contexts = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        body = ({"pal_name": "Echo interview", "layers": {"llm": {"api_key": "must-not-escape"}}}
                if method == "GET" else {"conversation_id": "c_test", "conversation_url": "https://room.invalid/test"})
        context = Context(Response(body))
        self.contexts.append(context)
        return context

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


def adapter(session):
    return TavusSessionAdapter(session, face_id="face_test", pal_id="pal_echo", max_duration_seconds=60)


async def test_current_api_payload_has_duration_cap_and_preserves_auth():
    session = Session()
    headers = {"x-api-key": "unit-test-key", "Content-Type": "application/json"}
    legacy = {"replica_id": "face_test", "persona_id": "pal_echo"}
    async with adapter(session).post(TAVUS_BASE_URL + "/conversations", json=legacy, headers=headers) as response:
        assert (await response.json())["conversation_id"] == "c_test"
    method, url, args = session.calls[0]
    assert method == "POST" and url == TAVUS_BASE_URL + "/conversations"
    assert args["json"] == {
        "face_id": "face_test", "pal_id": "pal_echo",
        "properties": {"max_call_duration": 60, "participant_left_timeout": 10,
                       "participant_absent_timeout": 20, "enable_recording": False,
                       "auto_start_recording": False},
    }
    assert args["headers"] == headers and args["allow_redirects"] is False
    assert legacy == {"replica_id": "face_test", "persona_id": "pal_echo"}
    assert session.contexts[0].closed


async def test_metadata_uses_pals_and_does_not_return_tool_credentials():
    session = Session()
    async with adapter(session).get(TAVUS_BASE_URL + "/personas/pal_echo", headers={"x-api-key": "unit-test-key"}) as response:
        response.raise_for_status()
        assert await response.json() == {"persona_name": "Echo interview"}
    assert session.calls[0][1] == TAVUS_BASE_URL + "/pals/pal_echo"
    assert session.calls[0][2]["allow_redirects"] is False
    assert session.contexts[0].closed


async def test_end_conversation_keeps_current_endpoint():
    session = Session()
    async with adapter(session).post(TAVUS_BASE_URL + "/conversations/c_test/end") as response:
        response.raise_for_status()
    assert session.calls == [("POST", TAVUS_BASE_URL + "/conversations/c_test/end", {"allow_redirects": False})]


@pytest.mark.parametrize("method,url,kwargs", [
    ("post", "https://other.invalid/v2/conversations", {}),
    ("get", TAVUS_BASE_URL + "/personas/another_pal", {}),
    ("post", TAVUS_BASE_URL + "/conversations/../end", {}),
    ("post", TAVUS_BASE_URL + "/conversations", {"json": {"replica_id": "other", "persona_id": "pal_echo"}}),
])
def test_unknown_calls_are_rejected_before_network(method, url, kwargs):
    session = Session()
    with pytest.raises(TavusCompatibilityError):
        getattr(adapter(session), method)(url, **kwargs)
    assert not session.calls


@pytest.mark.parametrize("duration", [0, -1, 1801, True, 1.5])
def test_invalid_provider_duration_is_rejected(duration):
    with pytest.raises(TavusCompatibilityError):
        TavusSessionAdapter(Session(), face_id="face", pal_id="pal", max_duration_seconds=duration)


def test_disabled_tavus_does_not_construct_service_or_make_requests():
    session = Session()
    with pytest.raises(TavusCompatibilityError, match="not enabled"):
        create_tavus_video_service(Settings(_env_file=None), session, max_duration_seconds=60)
    assert not session.calls


async def test_pinned_sdk_uses_adapter_for_create_metadata_and_end(monkeypatch):
    pytest.importorskip("pipecat")
    pytest.importorskip("daily")
    from pipecat.transports.tavus.transport import TavusApi
    monkeypatch.delenv("TAVUS_SAMPLE_ROOM_URL", raising=False)
    session = Session()
    api = TavusApi("unit-test-key", adapter(session))
    created = await api.create_conversation("face_test", "pal_echo")
    assert await api.get_persona_name("pal_echo") == "Echo interview"
    await api.end_conversation(created["conversation_id"])
    assert [call[1] for call in session.calls] == [
        TAVUS_BASE_URL + "/conversations", TAVUS_BASE_URL + "/pals/pal_echo",
        TAVUS_BASE_URL + "/conversations/c_test/end",
    ]
    assert session.calls[0][2]["json"]["face_id"] == "face_test"
    assert "replica_id" not in session.calls[0][2]["json"]


def test_service_factory_supports_actual_pinned_constructor_without_network():
    pytest.importorskip("pipecat")
    pytest.importorskip("daily")
    session = Session()
    settings = Settings(_env_file=None, realtime_enabled=True, tavus_enabled=True, avatar_mode="tavus",
                        tavus_api_key="unit-test-key", tavus_face_id="face_test", tavus_pal_id="pal_echo")
    service = create_tavus_video_service(settings, session, max_duration_seconds=60)
    assert service._replica_id == "face_test" and service._persona_id == "pal_echo"
    assert isinstance(service._session, TavusSessionAdapter)
    assert not session.calls
