import pytest
from fastapi.testclient import TestClient

from ai_interviewer.config import Settings
from ai_interviewer.runtime import StartupError, build_app


def settings(tmp_path, **changes):
    return Settings(_env_file=None, admin_api_key="a" * 40, ip_hash_secret="b" * 40,
                    privacy_contact="Equipo de pruebas sintéticas", data_dir=tmp_path / "data", **changes)


def test_mock_composition_runs_protected_synthetic_flow(tmp_path):
    with TestClient(build_app(settings(tmp_path))) as client:
        assert client.get("/").json()["mode"] == "mock"
        assert client.get("/admin/health").status_code == 401
        headers = {"X-Admin-Key": "a" * 40}
        created = client.post("/admin/interviews", headers=headers, json={"role_id": "pm_po", "name": "Synthetic", "email": "synthetic@example.invalid"})
        assert created.status_code == 201, created.text
        token = created.json()["link"].split("/")[-1]
        assert client.post(f"/i/{token}/start").status_code == 409
        assert client.post(f"/i/{token}/consent", json={"accepted": True}).status_code == 200
        started = client.post(f"/i/{token}/start")
        assert started.status_code == 200
        interview_id = started.json()["id"]
        assert client.post(f"/session/{interview_id}/finish").status_code == 200
        report = client.post(f"/admin/interviews/{interview_id}/report", headers=headers)
        assert report.status_code == 200
        assert "mock_scoring" in report.json()["flags"]
        assert "candidate_end" in report.json()["flags"]
        assert all(item["score"] is None for item in report.json()["scores"])


@pytest.mark.parametrize("changes", [{"app_mode": "real"}, {"avatar_mode": "tavus"}])
def test_real_provider_settings_refused_before_creating_storage(tmp_path, changes):
    configured = settings(tmp_path, **changes)
    with pytest.raises(StartupError):
        build_app(configured)
    assert not configured.data_dir.exists()


def test_missing_settings_error_names_only_without_values(tmp_path):
    configured = Settings(_env_file=None, admin_api_key="DO-NOT-PRINT", privacy_contact="", data_dir=tmp_path)
    with pytest.raises(StartupError) as captured:
        build_app(configured)
    assert "PRIVACY_CONTACT" in str(captured.value)
    assert "DO-NOT-PRINT" not in str(captured.value)


def test_launcher_disables_access_logging_and_uses_one_local_worker(monkeypatch):
    import ai_interviewer.__main__ as launcher
    import uvicorn
    app = object()
    monkeypatch.setattr(launcher, "build_app", lambda: app)
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    assert launcher.main() == 0
    assert calls == [((app,), {"host": "127.0.0.1", "port": 8000, "workers": 1, "access_log": False})]


def test_explicit_mock_lan_http_supports_browser_origin(tmp_path):
    origin = "http://192.168.2.6:8000"
    app = build_app(settings(tmp_path, public_base_url=origin, allow_mock_lan_http=True))
    with TestClient(app, base_url=origin) as client:
        headers = {"X-Admin-Key": "a" * 40, "Origin": origin}
        response = client.post("/admin/interviews", headers=headers,
                               json={"role_id": "pm_po", "name": "Synthetic", "email": "synthetic@example.invalid"})
        assert response.status_code == 201
        link = response.json()["link"]
        assert link.startswith(origin + "/i/")
        assert client.post(link + "/consent", headers={"Origin": origin}, json={"accepted": True}).status_code == 200
        assert client.post(link + "/start", headers={"Origin": origin}).status_code == 200
        assert client.post(link + "/start", headers={"Origin": "http://other.invalid"}).status_code == 403


@pytest.mark.parametrize("origin,enabled", [("http://192.168.2.6:8000", False),
                                          ("http://8.8.8.8:8000", True),
                                          ("http://example.com:8000", True)])
def test_mock_lan_http_does_not_allow_other_insecure_origins(tmp_path, origin, enabled):
    with pytest.raises(ValueError, match="HTTPS"):
        build_app(settings(tmp_path, public_base_url=origin, allow_mock_lan_http=enabled))


def test_tavus_missing_fields_block_startup_with_current_names(tmp_path):
    with pytest.raises(StartupError) as captured:
        build_app(settings(tmp_path, realtime_enabled=True, tavus_enabled=True, avatar_mode="tavus"))
    assert "TAVUS_FACE_ID" in str(captured.value)
    assert "TAVUS_PAL_ID" in str(captured.value)
    assert "TAVUS_REPLICA_ID" not in str(captured.value)


def test_conversation_requires_anthropic_key_before_creating_storage(tmp_path):
    configured = settings(tmp_path, conversation_enabled=True)
    with pytest.raises(StartupError, match="ANTHROPIC_API_KEY"):
        build_app(configured)
    assert not configured.data_dir.exists()


def test_conversation_model_interprets_followups_while_scoring_remains_mock(tmp_path, monkeypatch):
    from ai_interviewer.engine import anthropic
    from ai_interviewer.engine.llm import AnswerAnalysis
    calls = []
    class Model:
        def __init__(self, *args, **kwargs): pass
        async def complete(self, system, user):
            calls.append(user)
            return AnswerAnalysis(concrete_example=len(calls) == 2,
                                  missing_component="result" if len(calls) == 1 else "none").model_dump_json()
    monkeypatch.setattr(anthropic, "AnthropicAnswerModel", Model)
    configured = settings(tmp_path, conversation_enabled=True, anthropic_api_key="unit-test-key")
    with TestClient(build_app(configured)) as client:
        assert client.get("/").json()["conversation"] == "anthropic"
        assert client.get("/").json()["scoring"] == "mock"
        headers = {"X-Admin-Key": "a" * 40}
        created = client.post("/admin/interviews", headers=headers,
                              json={"role_id": "pm_po", "name": "Synthetic", "email": "synthetic@example.invalid"}).json()
        path = "/i/" + created["link"].split("/")[-1]
        assert "Anthropic receives" in client.get(path).text
        assert client.post(path + "/start").status_code == 409
        client.post(path + "/consent", json={"accepted": True})
        client.post(path + "/start")
        session = "/session/" + created["id"]
        for text in ["Sí", "Dirijo un equipo de producto"]:
            assert client.post(session + "/turn", json={"text": text}).status_code == 200
        assert not calls
        followup = client.post(session + "/turn", json={"text": "En el proyecto de pagos entrevisté usuarios y cambié el flujo."}).json()
        assert "resultado concreto" in followup["text"]
        advanced = client.post(session + "/turn", json={"text": "Los errores bajaron un 20%."}).json()
        assert advanced["state"]["competency_index"] == 1
        assert len(calls) == 2 and "Synthetic" not in calls[0]
        assert client.post(session + "/finish").status_code == 200
        report = client.post("/admin/interviews/" + created["id"] + "/report", headers=headers).json()
        assert "mock_scoring" in report["flags"]
        assert all(item["score"] is None for item in report["scores"])


def test_old_consent_cannot_silently_authorize_anthropic(tmp_path):
    configured = settings(tmp_path)
    with TestClient(build_app(configured)) as client:
        created = client.post("/admin/interviews", headers={"X-Admin-Key": "a" * 40},
                              json={"role_id": "pm_po", "name": "Synthetic", "email": "synthetic@example.invalid"}).json()
        path = "/i/" + created["link"].split("/")[-1]
        client.post(path + "/consent", json={"accepted": True})
        client.post(path + "/start")
        configured.conversation_enabled = True
        assert client.post(path + "/start").status_code == 409
        session = "/session/" + created["id"]
        assert client.post(session + "/turn", json={"text": "Sí"}).status_code == 409
        assert client.post(session + "/finish").status_code == 200
        assert not (configured.data_dir / "conversation-budget.sqlite3").exists()
