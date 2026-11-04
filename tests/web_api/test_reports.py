import json
import sqlite3
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_interviewer.config import Settings
from ai_interviewer.runtime import build_app

ADMIN = {"X-Admin-Key": "a" * 40}


def configure(tmp_path, **kwargs):
    return Settings(_env_file=None, data_dir=tmp_path / "data", admin_api_key="a" * 40,
        ip_hash_secret="b" * 40, privacy_contact="Equipo", anthropic_api_key="unit-test-key",
        scoring_enabled=True, scoring_max_calls=6, **kwargs)


def begin(client):
    created = client.post("/admin/interviews", headers=ADMIN,
        json={"role_id": "pm_po", "name": "Synthetic <script>name</script>", "email": "synthetic@example.invalid"}).json()
    path = "/i/" + created["link"].split("/")[-1]
    assert "propose competency scores" in client.get(path).text
    client.post(path + "/consent", json={"accepted": True})
    client.post(path + "/start")
    return created["id"], path


def install_provider(monkeypatch, calls, *, invalid=False):
    from ai_interviewer.scoring import anthropic
    cls = anthropic.AnthropicScoringModel
    def handler(request):
        calls.append(request)
        payload = json.loads(json.loads(request.content)["messages"][0]["content"])
        scores = []
        for comp in payload["role"]["competencies"]:
            turns = [t for t in payload["transcript"] if t["competency_id"] == comp["id"]]
            enough = bool(turns)
            scores.append({"competency_id": comp["id"], "score": 3 if enough else None,
                "insufficient_evidence": not enough,
                "evidence_turn_ids": (["00000000-0000-0000-0000-000000000000"] if invalid else [turns[0]["id"]]) if enough else [],
                "rationale": "Presenta evidencia de una decisión y un resultado." if enough else "No se relató un caso de esta competencia."})
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps({"scores": scores})}]})
    monkeypatch.setattr(anthropic, "AnthropicScoringModel", lambda *args, **kwargs:
                        cls(*args, **kwargs, transport=httpx.MockTransport(handler)))


def test_finish_auto_generates_private_report_and_preserves_citations(tmp_path, monkeypatch):
    calls = []
    install_provider(monkeypatch, calls)
    settings = configure(tmp_path)
    with TestClient(build_app(settings)) as client:
        id, _ = begin(client)
        session = "/session/" + id
        for text in ["Sí", "Dirijo producto", "En pagos investigué el problema, cambié el flujo y bajaron los errores un 20%. <img src=x onerror=alert(1)>"]:
            assert client.post(session + "/turn", json={"text": text}).status_code == 200
        assert client.post(session + "/finish").status_code == 200
        for _ in range(100):
            response = client.get("/admin/interviews/" + id + "/report", headers=ADMIN)
            if response.status_code == 200: break
            time.sleep(.01)
        assert response.status_code == 200
        report = response.json()
        assert len(calls) == 3 and report["scores"][0]["score"] == 3
        assert all(s["score"] is None for s in report["scores"][1:])
        assert "mock_scoring" not in report["flags"]
        assert client.post("/admin/interviews/" + id + "/report", headers=ADMIN).json() == report
        assert len(calls) == 3  # cached, no repeat charge
        assert client.get("/admin/interviews").status_code == 401
        assert client.get("/admin/interviews/" + id + "/review").status_code == 401
        assert client.get("/admin/interviews/" + id + "/report.html").status_code == 401
        review = client.get("/admin/interviews/" + id + "/review", headers=ADMIN).json()
        assert report["scores"][0]["evidence_turn_ids"][0] == review["evidence"][0]["id"]
        assert {anchor["score"] for anchor in review["rubric"]["discovery"]} == {1, 3, 5}
        html = client.get("/admin/interviews/" + id + "/report.html", headers=ADMIN).text
        assert "Insufficient evidence" in html and "Human review pending" in html
        assert "<img" not in html and "&lt;img" in html
        assert client.get("/admin/review").status_code == 200
        overview = client.get("/admin/interviews", headers=ADMIN).json()["interviews"][0]
        assert overview["report_status"] == "ready" and overview["report_kind"] == "anthropic"
        with sqlite3.connect(settings.data_dir / "scoring-budget.sqlite3") as db:
            assert db.execute("SELECT calls FROM budget").fetchone()[0] == 3


def test_failed_validation_never_publishes_partial_report(tmp_path, monkeypatch):
    calls = []
    install_provider(monkeypatch, calls, invalid=True)
    with TestClient(build_app(configure(tmp_path, scoring_auto_generate=False))) as client:
        id, _ = begin(client)
        for text in ["Sí", "Dirijo producto", "Investigué un problema, cambié el flujo y observé una mejora."]:
            client.post("/session/" + id + "/turn", json={"text": text})
        client.post("/session/" + id + "/finish")
        assert client.post("/admin/interviews/" + id + "/report", headers=ADMIN).status_code == 503
        assert client.get("/admin/interviews/" + id + "/report", headers=ADMIN).status_code == 404
        assert client.get("/admin/interviews", headers=ADMIN).json()["interviews"][0]["report_status"] == "failed"
        assert len(calls) == 1


def test_old_consent_does_not_authorize_real_scoring(tmp_path):
    settings = configure(tmp_path, scoring_auto_generate=False)
    settings.scoring_enabled = False
    app = build_app(settings)
    with TestClient(app) as client:
        created = client.post("/admin/interviews", headers=ADMIN,
            json={"role_id": "pm_po", "name": "Synthetic", "email": "synthetic@example.invalid"}).json()
        path = "/i/" + created["link"].split("/")[-1]
        client.post(path + "/consent", json={"accepted": True});client.post(path + "/start")
        client.post("/session/" + created["id"] + "/finish")
        settings.scoring_enabled = True
        assert client.post("/admin/interviews/" + created["id"] + "/report", headers=ADMIN).status_code == 409
        assert not (settings.data_dir / "scoring-budget.sqlite3").exists()


def test_restart_marks_interrupted_report_as_retryable_without_provider_calls(tmp_path):
    settings = configure(tmp_path, scoring_auto_generate=False)
    app = build_app(settings)
    with TestClient(app) as client:
        id, _ = begin(client)
        client.post("/session/" + id + "/finish")
        from uuid import UUID
        client.portal.call(app.state.store.set_report_state, UUID(id), "running")
    with TestClient(build_app(settings)) as client:
        item = client.get("/admin/interviews", headers=ADMIN).json()["interviews"][0]
        assert item["report_status"] == "failed"
        assert not (settings.data_dir / "scoring-budget.sqlite3").exists()
