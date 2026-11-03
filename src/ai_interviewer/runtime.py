"""Composition root. Constructing mock mode never imports provider SDKs."""
from pathlib import Path

from ai_interviewer.config import Settings


class StartupError(Exception):
    """Safe diagnostics: field names and fixed messages only."""


def build_app(settings: Settings | None = None, *, roles_dir: Path = Path("roles")):
    settings = settings or Settings()
    if settings.app_mode != "mock":
        raise StartupError("APP_MODE=real is unavailable; use APP_MODE=mock.")
    if settings.avatar_mode != "mock":
        raise StartupError("APP_MODE=mock requires AVATAR_MODE=mock.")
    missing = settings.missing_secrets()
    if not settings.privacy_contact.strip():
        missing.append("PRIVACY_CONTACT")
    if missing:
        raise StartupError("Configure: " + ", ".join(missing))
    weak = [name for name in ("admin_api_key", "ip_hash_secret")
            if len(getattr(settings, name).get_secret_value()) < 32]
    if weak:
        raise StartupError("Use at least 32 random characters for: " + ", ".join(name.upper() for name in weak))

    from ai_interviewer.api import create_app
    from ai_interviewer.engine import StructuredInterviewEngine, load_role
    from ai_interviewer.scoring.scorer import InterviewScorer, MockScoringModel

    role = load_role(roles_dir / "pm_po.yaml")
    scorer = InterviewScorer(MockScoringModel())

    async def report_factory(interview, selected_role, turns):
        return await scorer.score(interview.id, selected_role, turns,
                                  flags=await app.state.store.get_flags(interview.id))

    app = create_app(settings, {role.id: role},
                     lambda: StructuredInterviewEngine(max_minutes=settings.interview_max_minutes),
                     privacy_contact=settings.privacy_contact, report_factory=report_factory)
    app.state.app_mode = "mock"
    app.state.mock_notice = "Demostración de texto sin voz ni video reales; no evalúa candidatos."

    @app.get("/")
    async def home():
        return {"mode": "mock", "notice": app.state.mock_notice,
                "next": "Crear invitación sintética mediante POST /admin/interviews con X-Admin-Key."}

    return app
