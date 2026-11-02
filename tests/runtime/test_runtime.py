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
