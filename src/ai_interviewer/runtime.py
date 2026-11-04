"""Composition root. Constructing mock mode never imports provider SDKs."""
from pathlib import Path

from ai_interviewer.config import Settings


class StartupError(Exception):
    """Safe diagnostics: field names and fixed messages only."""


def build_app(settings: Settings | None = None, *, roles_dir: Path = Path("roles")):
    settings = settings or Settings()
    if settings.app_mode != "mock":
        raise StartupError("APP_MODE=real is unavailable; use APP_MODE=mock.")
    if (settings.conversation_enabled or settings.scoring_enabled) and (not settings.anthropic_api_key or not settings.anthropic_api_key.get_secret_value().strip()):
        raise StartupError("Configure: ANTHROPIC_API_KEY")
    if settings.avatar_mode != "mock" and not (settings.realtime_enabled and settings.tavus_enabled):
        raise StartupError("APP_MODE=mock requires AVATAR_MODE=mock.")
    if settings.tavus_enabled:
        missing_avatar = settings.missing_tavus_settings()
        if missing_avatar:
            raise StartupError("Configure: " + ", ".join(missing_avatar))
        if not settings.realtime_enabled or settings.avatar_mode != "tavus":
            raise StartupError("TAVUS_ENABLED requires REALTIME_ENABLED=true and AVATAR_MODE=tavus.")
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
    scoring_budget = None
    if settings.scoring_enabled:
        from ai_interviewer.engine.anthropic import CallBudget
        scoring_budget = CallBudget(settings.data_dir / "scoring-budget.sqlite3", settings.scoring_max_calls)
    answer_model = None
    if settings.conversation_enabled:
        from ai_interviewer.engine.anthropic import AnthropicAnswerModel, CallBudget
        answer_model = AnthropicAnswerModel(settings.anthropic_api_key, model=settings.conversation_model,
            budget=CallBudget(settings.data_dir / "conversation-budget.sqlite3", settings.conversation_max_calls),
            timeout_seconds=settings.conversation_timeout_seconds)

    def engine_factory():
        from ai_interviewer.engine.llm import LLMAnswerAnalyzer
        return StructuredInterviewEngine(
            analyzer=LLMAnswerAnalyzer(answer_model) if answer_model else None,
            context_first=settings.realtime_enabled, auto_language=settings.realtime_enabled,
            max_minutes=settings.interview_max_minutes, mock_single_followup=not settings.conversation_enabled,
            llm_timeout=settings.conversation_timeout_seconds if answer_model else 5)

    async def report_factory(interview, selected_role, turns):
        selected_scorer = scorer
        if settings.scoring_enabled:
            import asyncio
            from ai_interviewer.engine.anthropic import ReservedCalls
            from ai_interviewer.scoring.anthropic import AnthropicScoringModel
            # Reserve all three attempts together, across interviews and restarts.
            await asyncio.to_thread(scoring_budget.reserve, 3)
            selected_scorer = InterviewScorer(AnthropicScoringModel(
                settings.anthropic_api_key, model=settings.scoring_model, budget=ReservedCalls(3),
                timeout_seconds=settings.scoring_timeout_seconds), timeout=settings.scoring_timeout_seconds)
        return await selected_scorer.score(interview.id, selected_role, turns,
                                  flags=await app.state.store.get_flags(interview.id))

    app = create_app(settings, {role.id: role},
                     engine_factory,
                     privacy_contact=settings.privacy_contact, report_factory=report_factory)
    app.state.app_mode = "mock"
    app.state.conversation_mode = "anthropic" if settings.conversation_enabled else "mock"
    app.state.scoring_mode = "anthropic" if settings.scoring_enabled else "mock"
    app.state.server_options = {"port": settings.listen_port}
    if bool(settings.tls_cert_file) != bool(settings.tls_key_file):
        raise StartupError("Configure both TLS_CERT_FILE and TLS_KEY_FILE.")
    if settings.tls_cert_file:
        app.state.server_options.update(ssl_certfile=str(settings.tls_cert_file), ssl_keyfile=str(settings.tls_key_file))
    app.state.mock_notice = "Text interview demo."
    if settings.realtime_enabled:
        app.state.mock_notice = ("Demo with local Whisper/Piper audio and Tavus avatar enabled." if settings.tavus_enabled else
                                 "Demo with local Whisper/Piper audio; avatar not enabled.")
    if settings.conversation_enabled:
        app.state.mock_notice += " Claude interprets answers."
    app.state.mock_notice += (" Claude report with textual evidence, pending human review." if settings.scoring_enabled else
                             " Reports use mock scoring without real scores.")

    @app.get("/")
    async def home():
        return {"mode": "mock", "notice": app.state.mock_notice,
                "conversation": app.state.conversation_mode, "scoring": app.state.scoring_mode,
                "next": "Create a synthetic invitation via POST /admin/interviews with X-Admin-Key."}

    return app
