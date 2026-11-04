from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from ai_interviewer.api import create_app
from ai_interviewer.config import Settings
from ai_interviewer.engine import StructuredInterviewEngine, load_role


class MediaDouble:
    def __init__(self):
        self.peers = {}
        self.calls = []
        self.closed = []

    async def prepare(self):
        pass

    async def offer(self, interview_id, **kwargs):
        self.calls.append((interview_id, kwargs))
        return {"sdp": "synthetic answer", "type": "answer", "pc_id": "test"}

    async def close(self, interview_id):
        self.closed.append(interview_id)

    async def close_all(self):
        pass


def test_media_requires_session_and_versioned_consent_and_reuses_engine(tmp_path):
    role = load_role(Path("roles/pm_po.yaml"))
    settings = Settings(_env_file=None, admin_api_key="a" * 40, ip_hash_secret="b" * 40,
                        public_base_url="https://localhost:8443", data_dir=tmp_path,
                        realtime_enabled=True, turn_url="turn:localhost:3479?transport=tcp",
                        turn_shared_secret="t" * 40)
    media = MediaDouble()
    app = create_app(settings, {role.id: role}, StructuredInterviewEngine,
                     privacy_contact="Equipo", media_manager=media)
    with TestClient(app, base_url=settings.public_base_url) as client:
        created = client.post("/admin/interviews", headers={"X-Admin-Key": "a" * 40},
                              json={"role_id": role.id, "name": "Synthetic", "email": "synthetic@example.invalid"}).json()
        path = created["link"]
        session = "/session/" + created["id"]
        body = {"sdp": "synthetic offer", "type": "offer"}
        assert client.post(session + "/offer", json=body).status_code == 409
        notice = client.get(path).text
        assert "Whisper and Piper" in notice and "not audio files" in notice
        assert client.post(path + "/consent", json={"accepted": True}).status_code == 200
        assert client.post(path + "/start").status_code == 200
        assert client.post(session + "/offer", headers={"Origin": "https://other.invalid"}, json=body).status_code == 403
        assert client.post(session + "/offer", json=body).status_code == 200
        config = client.post(session + "/media/config").json()
        assert config["iceTransportPolicy"] == "relay"
        assert config["iceServers"][0]["credential"] != settings.turn_shared_secret.get_secret_value()
        submit = media.calls[0][1]["submit"]
        import asyncio
        decision = client.portal.call(submit, "Sí, podemos empezar")
        assert decision["state"]["phase"] == "warmup"
        assert client.post(session + "/finish").status_code == 200
        assert media.closed
        assert client.post(session + "/offer", json=body).status_code == 409


def test_text_consent_cannot_authorize_new_media_recipient(tmp_path):
    role = load_role(Path("roles/pm_po.yaml"))
    settings = Settings(_env_file=None, admin_api_key="a" * 40, ip_hash_secret="b" * 40,
                        public_base_url="https://localhost:8443", data_dir=tmp_path)
    media = MediaDouble()
    app = create_app(settings, {role.id: role}, StructuredInterviewEngine,
                     privacy_contact="Equipo", media_manager=media)
    with TestClient(app, base_url=settings.public_base_url) as client:
        value = client.post("/admin/interviews", headers={"X-Admin-Key": "a" * 40},
                            json={"role_id": role.id, "name": "Synthetic", "email": "synthetic@example.invalid"}).json()
        client.post(value["link"] + "/consent", json={"accepted": True})
        client.post(value["link"] + "/start")
        settings.realtime_enabled = True
        response = client.post("/session/" + value["id"] + "/offer", json={"sdp": "offer", "type": "offer"})
        assert response.status_code == 409
        assert not media.calls
