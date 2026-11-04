from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ai_interviewer.api import create_app
from ai_interviewer.config import Settings
from ai_interviewer.contracts import (
    CompetencyScore, EngineDecision, InterviewPhase, InterviewReport, InterviewState, Turn,
)
from ai_interviewer.engine.roles import load_role
from ai_interviewer.storage import SQLiteSessionStore


class Clock:
    def __init__(self):
        self.value = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


class Engine:
    restored = 0

    def __init__(self):
        self.turns = []
        self.state = InterviewState(phase=InterviewPhase.WARMUP)

    def decision(self, text):
        self.turns.append(Turn(speaker="interviewer", text=text, ts_start=self.state.elapsed_seconds, ts_end=self.state.elapsed_seconds, phase=self.state.phase))
        return EngineDecision(state=self.state, text=text, end_session=self.state.phase == InterviewPhase.DONE)

    async def start(self, role, candidate):
        return self.decision("Soy un AI interviewer; esta entrevista se graba y la revisa una persona. Contame sobre tu experiencia.")

    async def on_candidate_turn(self, turn):
        self.turns.append(turn)
        self.state = self.state.model_copy(update={"elapsed_seconds": turn.ts_end})
        return self.decision("Gracias. ¿Qué resultado obtuviste?")

    async def on_event(self, event):
        self.state = InterviewState(phase=InterviewPhase.DONE, elapsed_seconds=event.elapsed_seconds)
        return self.decision("Gracias por tu tiempo.")

    async def restore(self, role, candidate, snapshot, turns):
        type(self).restored += 1
        self.state, self.turns = snapshot.state, list(turns)

    def transcript(self):
        return list(self.turns)




@pytest.fixture
def setup(tmp_path):
    clock = Clock()
    role = load_role(Path(__file__).resolve().parents[2] / "roles" / "pm_po.yaml")
    settings = Settings(_env_file=None, data_dir=tmp_path, public_base_url="http://localhost", admin_api_key=SecretStr("test-admin-key"), ip_hash_secret=SecretStr("test-ip-secret"))
    store = SQLiteSessionStore(tmp_path)
    app = create_app(settings, {role.id: role}, Engine, privacy_contact="Equipo de prueba", store=store, clock=clock, watchdog_interval=.02)
    with TestClient(app, base_url="http://localhost") as client:
        yield client, app, store, clock, role, settings
    store.close()


def invite(client, role):
    response = client.post("/admin/interviews", headers={"X-Admin-Key": "test-admin-key"}, json={"role_id": role.id, "name": "Candidato", "email": "candidate@example.test"})
    assert response.status_code == 201
    data = response.json()
    return UUID(data["id"]), data["link"].replace("http://localhost", "")


def begin(client, role):
    interview_id, link = invite(client, role)
    assert client.post(link + "/consent", json={"accepted": True}).status_code == 200
    response = client.post(link + "/start")
    assert response.status_code == 200
    return interview_id, link, response


def test_link_consent_text_finish_survey_and_delete(setup):
    client, app, store, clock, role, _ = setup
    interview_id, link = invite(client, role)
    page = client.get(link)
    assert "AI interviewer" in page.text
    assert "Equipo de prueba" in page.text
    assert "30 days" in page.text
    assert client.get(link + "/room").status_code == 403
    assert client.post(link + "/start").status_code == 409
    assert client.post(link + "/consent", json={"accepted": False}).status_code == 422
    assert client.post(link + "/consent", json={"accepted": True}).status_code == 200
    room = client.get(link + "/room")
    assert room.status_code == 200
    assert "Audio and avatar are not available yet" in room.text
    response = client.post(link + "/start")
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    clock.value += timedelta(seconds=4)
    answer = client.post(f"/session/{interview_id}/turn", json={"text": "Lideré un discovery y medimos su impacto."})
    assert answer.status_code == 200
    turns = client.portal.call(store.transcript, interview_id)
    assert len(turns) == 3
    assert [turn.speaker for turn in turns] == ["interviewer", "candidate", "interviewer"]
    assert client.post(f"/session/{interview_id}/offer").status_code == 503
    assert client.post(f"/session/{interview_id}/finish").json()["end_session"] is True
    assert client.post(f"/session/{interview_id}/turn", json={"text": "Otra"}).status_code == 409
    assert client.post(f"/session/{interview_id}/survey", json={"clarity": 5, "fairness": 4, "comment": "Gracias"}).status_code == 200
    assert client.get(f"/admin/interviews/{interview_id}/report").status_code == 401
    assert client.get(f"/admin/interviews/{interview_id}/report", headers={"X-Admin-Key": "test-admin-key"}).status_code == 404
    assert client.delete(f"/admin/interviews/{interview_id}", headers={"X-Admin-Key": "test-admin-key"}).status_code == 204
    assert client.portal.call(store.get, interview_id) is None
    assert client.portal.call(store.transcript, interview_id) == []


def test_admin_auth_token_expiry_and_single_use(setup):
    client, app, store, clock, role, _ = setup
    assert client.post("/admin/interviews", json={"role_id": role.id, "name": "A", "email": "a@b"}).status_code == 401
    interview_id, link, _ = begin(client, role)
    assert client.get(link).status_code == 410
    assert client.post(link + "/consent", json={"accepted": True}).status_code == 409
    # Token alone cannot claim or resume an active session from another browser.
    with TestClient(app, base_url="http://localhost") as stranger:
        assert stranger.post(link + "/start").status_code == 409
        assert stranger.get(link + "/room").status_code == 409
        assert stranger.post(f"/session/{interview_id}/finish").status_code == 409
    second_id, second_link = invite(client, role)
    clock.value += timedelta(days=8)
    assert client.get(second_link).status_code == 410
    assert client.post(second_link + "/consent", json={"accepted": True}).status_code == 409


def test_deadline_runs_without_candidate_request(setup):
    client, app, store, clock, role, _ = setup
    interview_id, link, _ = begin(client, role)
    clock.value += timedelta(minutes=31)
    client.portal.call(app.state.enforce_deadlines)
    interview = client.portal.call(store.get, interview_id)
    assert interview.status == "completed"
    snapshot = client.portal.call(store.get_snapshot, interview_id)
    assert snapshot.state.phase == InterviewPhase.DONE
    assert snapshot.deadline == interview.started_at + timedelta(minutes=30)
    assert client.post(link + "/start").status_code == 409


def test_resume_after_app_restart_uses_original_state(setup):
    client, app, store, clock, role, settings = setup
    interview_id, link, _ = begin(client, role)
    assert client.post(f"/session/{interview_id}/turn", json={"text": "Ejemplo concreto"}).status_code == 200
    snapshot = client.portal.call(store.get_snapshot, interview_id)
    Engine.restored = 0
    restarted = create_app(settings, {role.id: role}, Engine, privacy_contact="Equipo", store=store, clock=clock)
    with TestClient(restarted, base_url="http://localhost", cookies=client.cookies) as restored:
        response = restored.post(link + "/start")
        assert response.status_code == 200 and response.json()["resumed"] is True
        assert Engine.restored == 1
        assert restored.post(f"/session/{interview_id}/turn", json={"text": "Continuación"}).status_code == 200
        assert restored.portal.call(store.get_snapshot, interview_id).deadline == snapshot.deadline
        assert len(restored.portal.call(store.transcript, interview_id)) == 5


def test_security_headers_csrf_validation_and_contact(setup):
    client, app, store, clock, role, settings = setup
    _, link = invite(client, role)
    response = client.get(link)
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.post(link + "/consent", json={"accepted": True}, headers={"Origin": "https://untrusted.test"}).status_code == 403
    response = client.post(link + "/consent", json={"accepted": "sensitive-input"})
    assert response.status_code == 422 and "sensitive-input" not in response.text
    assert client.post(link + "/consent", content="x" * 20001).status_code == 413
    with pytest.raises(ValueError, match="privacy_contact"):
        create_app(settings, {role.id: role}, Engine, privacy_contact="", store=store)
    insecure = settings.model_copy(update={"public_base_url": "http://192.168.2.6"})
    with pytest.raises(ValueError, match="HTTPS"):
        create_app(insecure, {role.id: role}, Engine, privacy_contact="Equipo", store=store)


def test_opt_in_report_generation_validates_and_is_idempotent(setup):
    client, app, store, clock, role, settings = setup
    interview_id, link, _ = begin(client, role)
    assert client.post(f"/session/{interview_id}/finish").status_code == 200
    calls = []

    async def generate(interview, spec, turns):
        calls.append(interview.id)
        return InterviewReport(interview_id=interview.id, role_id=spec.id, role_version=spec.version, generated_at=clock(), summary="Sin evidencia suficiente", recommendation="Revisar con una persona", scores=[CompetencyScore(competency_id=c.id, score=None, evidence_turn_ids=[], rationale="Sin evidencia", insufficient_evidence=True) for c in spec.competencies])

    reporting = create_app(settings, {role.id: role}, Engine, privacy_contact="Equipo", store=store, clock=clock, report_factory=generate)
    with TestClient(reporting, base_url="http://localhost") as reporter:
        path = f"/admin/interviews/{interview_id}/report"
        assert reporter.post(path).status_code == 401
        response = reporter.post(path, headers={"X-Admin-Key": "test-admin-key"})
        assert response.status_code == 200
        assert reporter.post(path, headers={"X-Admin-Key": "test-admin-key"}).json() == response.json()
        assert reporter.get(path, headers={"X-Admin-Key": "test-admin-key"}).json() == response.json()
    assert calls == [interview_id]

async def test_watchdog_waiting_for_slow_start_reads_committed_snapshot(tmp_path):
    import asyncio
    import httpx

    clock = Clock()
    role = load_role(Path(__file__).resolve().parents[2] / "roles" / "pm_po.yaml")
    settings = Settings(_env_file=None, data_dir=tmp_path, public_base_url="http://localhost", admin_api_key=SecretStr("test-admin-key"), ip_hash_secret=SecretStr("test-ip-secret"))
    store = SQLiteSessionStore(tmp_path)
    started, release = asyncio.Event(), asyncio.Event()

    class SlowStart(Engine):
        async def start(self, role, candidate):
            started.set()
            await release.wait()
            return await super().start(role, candidate)

    app = create_app(settings, {role.id: role}, SlowStart, privacy_contact="Equipo", store=store, clock=clock, watchdog_interval=3600)
    try:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
                created = await client.post("/admin/interviews", headers={"X-Admin-Key": "test-admin-key"}, json={"role_id": role.id, "name": "Candidato", "email": "a@b.test"})
                data = created.json()
                path = data["link"].replace("http://localhost", "")
                await client.post(path + "/consent", json={"accepted": True})
                pending_start = asyncio.create_task(client.post(path + "/start"))
                await asyncio.wait_for(started.wait(), timeout=2)
                pending_watchdog = asyncio.create_task(app.state.enforce_deadlines())
                # Let watchdog inspect the claimed session and block behind start's lock.
                await asyncio.sleep(0)
                release.set()
                response, _ = await asyncio.gather(pending_start, pending_watchdog)
                assert response.status_code == 200
                interview = await store.get(UUID(data["id"]))
                assert interview.status == "active"
                assert (await store.get_snapshot(interview.id)).state.phase == InterviewPhase.WARMUP
                assert (await client.post(f"/session/{interview.id}/turn", json={"text": "Primera respuesta"})).status_code == 200
    finally:
        store.close()


@pytest.mark.parametrize("failure", ["engine_error", "engine_timeout", "progress_error"])
def test_finish_failure_closes_store_and_discards_mutated_engine(setup, monkeypatch, failure):
    import asyncio
    import gc
    import weakref

    client, _, store, clock, role, settings = setup
    references = []

    class FailedEnd(Engine):
        async def on_event(self, event):
            # Mutate first, as an actual engine may before a provider/storage failure.
            decision = await super().on_event(event)
            if failure == "engine_error":
                raise RuntimeError("provider failed")
            if failure == "engine_timeout":
                await asyncio.Event().wait()
            return decision

    def factory():
        engine = FailedEnd()
        references.append(weakref.ref(engine))
        return engine

    app = create_app(settings, {role.id: role}, factory, privacy_contact="Equipo", store=store, clock=clock)
    with TestClient(app, base_url="http://localhost") as failing:
        interview_id, _, _ = begin(failing, role)
        original = store.save_progress
        if failure == "progress_error":
            async def broken_progress(*args, **kwargs):
                raise OSError("disk write failed")
            monkeypatch.setattr(store, "save_progress", broken_progress)
        response = failing.post(f"/session/{interview_id}/finish")
        assert response.status_code == 503
        assert "ended" in response.json()["detail"]
        interview = failing.portal.call(store.get, interview_id)
        assert interview.status == "aborted" and interview.ended_at == clock()
        assert failing.post(f"/session/{interview_id}/turn", json={"text": "No continuar"}).status_code == 409
        assert failing.post(f"/session/{interview_id}/finish").status_code == 409
        monkeypatch.setattr(store, "save_progress", original)
        gc.collect()
        assert references and all(reference() is None for reference in references)
