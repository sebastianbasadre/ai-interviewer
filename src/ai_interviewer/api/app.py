"""Minimal pilot web API with injected interview engine and no provider calls."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Mapping
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from ai_interviewer.config import Settings
from ai_interviewer.contracts import (
    Candidate, ConsentRecord, EngineDecision, EngineEvent, Interview, InterviewEngine,
    InterviewPhase, InterviewReport, RoleSpec, SessionSnapshot, Turn,
)
from ai_interviewer.storage import SQLiteSessionStore, StorageError
from ai_interviewer.storage.sqlite import token_hash
from .pages import CONSENT_JS, ROOM_JS, consent_page, room_page

CONSENT_VERSION = "pilot-v1"


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class NewInterview(Input):
    role_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)


class ConsentInput(Input):
    accepted: bool = Field(strict=True)


class CandidateText(Input):
    text: str = Field(min_length=1, max_length=12000)


class Survey(Input):
    clarity: int = Field(ge=1, le=5, strict=True)
    fairness: int = Field(ge=1, le=5, strict=True)
    comment: str = Field(default="", max_length=2000)


def create_app(
    settings: Settings,
    roles: Mapping[str, RoleSpec],
    engine_factory: Callable[[], InterviewEngine],
    *,
    privacy_contact: str,
    store: SQLiteSessionStore | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    retention_interval: float = 3600,
    watchdog_interval: float = 1,
    report_factory: Callable[[Interview, RoleSpec, list[Turn]], Awaitable[InterviewReport]] | None = None,
) -> FastAPI:
    """Construct explicitly. Run uvicorn with access_log=False: invitation URLs are secrets.

    privacy_contact must identify the person/team who handles deletion requests. Audio/video
    signaling is deliberately unavailable until an inspected Pipecat adapter is integrated.
    """
    if settings.missing_secrets():
        raise ValueError("ADMIN_API_KEY and IP_HASH_SECRET must be configured")
    if not privacy_contact.strip():
        raise ValueError("privacy_contact is required before inviting candidates")
    base = settings.public_base_url.rstrip("/")
    origin = urlsplit(base)
    if origin.scheme not in {"http", "https"} or not origin.hostname or origin.path not in {"", "/"} or origin.query or origin.fragment or origin.username:
        raise ValueError("PUBLIC_BASE_URL must be an origin without credentials or path")
    if origin.scheme != "https" and origin.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("HTTPS required outside localhost")
    if retention_interval <= 0 or watchdog_interval <= 0:
        raise ValueError("maintenance intervals must be positive")
    owned_store = store is None
    repository = store or SQLiteSessionStore(settings.data_dir)
    engines: dict[UUID, InterviewEngine] = {}
    locks: dict[UUID, asyncio.Lock] = {}
    # No client IP is retained in rate-limiter keys: HMAC only, no request logging.
    requests: dict[str, deque[float]] = defaultdict(deque)

    async def purge() -> None:
        await repository.purge_expired(clock() - timedelta(days=settings.retention_days))

    async def retention_job() -> None:
        while True:
            await asyncio.sleep(retention_interval)
            try:
                await purge()
            except Exception:
                # Safe diagnostic only; never include row/exception content.
                app.state.retention_healthy = False
            else:
                app.state.retention_healthy = True

    async def enforce_deadlines() -> None:
        """Also runs after process restart; client traffic cannot extend the deadline."""
        for interview in await repository.active():
            async with locks.setdefault(interview.id, asyncio.Lock()):
                current = await repository.get(interview.id)
                if not current or current.status != "active":
                    continue
                # start() owns this lock until its first snapshot is committed. Read only
                # after acquiring it: a pre-lock missing/expired snapshot can be stale.
                snapshot = await repository.get_snapshot(interview.id)
                if snapshot and clock() < snapshot.deadline:
                    continue
                try:
                    if not snapshot:
                        await repository.finish(interview.id, clock(), aborted=True)
                        continue
                    engine, snapshot = await get_engine(current)
                    decision = await asyncio.wait_for(engine.on_event(EngineEvent(kind="deadline_reached", elapsed_seconds=max(0, (clock() - current.started_at).total_seconds()))), timeout=2)
                    if not decision.end_session:
                        raise StorageError("deadline must end session")
                    await persist(current, engine, decision, snapshot.deadline)
                except Exception:
                    # Never keep a provider/engine failure active after the hard deadline.
                    current = await repository.get(interview.id)
                    if current and current.status == "active":
                        await repository.finish(interview.id, clock(), aborted=True)
                    engines.pop(interview.id, None)

    async def watchdog() -> None:
        while True:
            await asyncio.sleep(watchdog_interval)
            try:
                await enforce_deadlines()
            except Exception:
                app.state.sessions_healthy = False
            else:
                app.state.sessions_healthy = True

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await purge()
        await enforce_deadlines()
        app.state.retention_healthy = True
        app.state.sessions_healthy = True
        tasks = [asyncio.create_task(retention_job()), asyncio.create_task(watchdog())]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if owned_store:
                repository.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = repository
    app.state.enforce_deadlines = enforce_deadlines

    @app.exception_handler(StorageError)
    async def storage_error(request: Request, error: StorageError):
        return JSONResponse({"detail": "Entrevista o sesión no disponible."}, status_code=409)

    # Validation errors can contain candidate text; never echo Pydantic's input values.
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError):
        return JSONResponse({"detail": "Datos inválidos."}, status_code=422)

    @app.middleware("http")
    async def security(request: Request, call_next):
        now = time.monotonic()
        ip = request.client.host if request.client else "unknown"
        digest = hmac.new(settings.ip_hash_secret.get_secret_value().encode(), ip.encode(), hashlib.sha256).hexdigest()
        bucket = requests[digest]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        # Bound in-memory bookkeeping; this is per-process pilot protection, not distributed.
        if len(requests) > 10000:
            for key in list(requests):
                if not requests[key] or requests[key][-1] <= now - 60:
                    del requests[key]
        if len(bucket) >= 120 or len(requests) > 10000:
            response = JSONResponse({"detail": "Demasiadas solicitudes."}, status_code=429, headers={"Retry-After": "60"})
        elif request.method not in {"GET", "HEAD", "OPTIONS"} and request.headers.get("origin") not in {None, base}:
            response = JSONResponse({"detail": "Origen no permitido."}, status_code=403)
        elif request.headers.get("content-length", "").isdigit() and int(request.headers["content-length"]) > 20000:
            response = JSONResponse({"detail": "Solicitud demasiado grande."}, status_code=413)
        else:
            bucket.append(now)
            response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; media-src 'self' blob:; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "Permissions-Policy": "camera=(self), microphone=(self)",
        })
        if origin.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    async def admin(x_admin_key: str = Header(default="")) -> None:
        if not secrets.compare_digest(x_admin_key, settings.admin_api_key.get_secret_value()):
            raise HTTPException(401, "Autenticación requerida.")

    @app.get("/admin/health", dependencies=[Depends(admin)])
    async def health():
        healthy = bool(getattr(app.state, "retention_healthy", False) and getattr(app.state, "sessions_healthy", False))
        return JSONResponse({"healthy": healthy, "retention": getattr(app.state, "retention_healthy", False), "session_deadlines": getattr(app.state, "sessions_healthy", False)}, status_code=200 if healthy else 503)

    def cookie_name(interview_id: UUID) -> str:
        return f"session_{interview_id.hex}"

    async def authorize(request: Request, interview_id: UUID, *, finished: bool = False) -> Interview:
        key = request.cookies.get(cookie_name(interview_id), "")
        return await repository.authorize(interview_id, key, clock(), allow_finished=finished)

    async def get_engine(interview: Interview) -> tuple[InterviewEngine, SessionSnapshot]:
        snapshot = await repository.get_snapshot(interview.id)
        if not snapshot:
            raise StorageError("session state unavailable")
        if interview.id not in engines:
            role = roles.get(interview.role_id)
            if role is None or role.version != interview.role_version:
                raise StorageError("role version unavailable")
            engine = engine_factory()
            await engine.restore(role, interview.candidate, snapshot, await repository.transcript(interview.id))
            engines[interview.id] = engine
        return engines[interview.id], snapshot

    async def persist(interview: Interview, engine: InterviewEngine, decision: EngineDecision, deadline: datetime) -> None:
        # Store every turn before exposing decision, so reconnect never fabricates missing evidence.
        await repository.save_progress(SessionSnapshot(interview_id=interview.id, state=decision.state, deadline=deadline, updated_at=clock()), engine.transcript(), decision.flags)
        if decision.end_session:
            await repository.finish(interview.id, clock())
            engines.pop(interview.id, None)

    @app.post("/admin/interviews", dependencies=[Depends(admin)], status_code=201)
    async def create_interview(body: NewInterview):
        role = roles.get(body.role_id)
        if role is None:
            raise HTTPException(422, "Rol no disponible.")
        token = secrets.token_urlsafe(32)
        now = clock()
        interview = Interview(candidate=Candidate(name=body.name, email=body.email), role_id=role.id, role_version=role.version, token_hash=token_hash(token), created_at=now, expires_at=now + timedelta(days=7))
        await repository.create(interview)
        return {"id": str(interview.id), "link": f"{base}/i/{token}", "expires_at": interview.expires_at.isoformat()}

    @app.get("/i/{token}", response_class=HTMLResponse)
    async def invitation(token: str):
        interview = await repository.by_token(token_hash(token))
        if interview.status not in {"invited", "consented"} or clock() >= interview.expires_at:
            raise HTTPException(410, "Invitación vencida o utilizada.")
        return consent_page(token, settings.retention_days, privacy_contact)

    @app.post("/i/{token}/consent")
    async def consent(token: str, body: ConsentInput, request: Request):
        if not body.accepted:
            raise HTTPException(422, "Se requiere consentimiento explícito.")
        interview = await repository.by_token(token_hash(token))
        ip = request.client.host if request.client else "unknown"
        digest = hmac.new(settings.ip_hash_secret.get_secret_value().encode(), ip.encode(), hashlib.sha256).hexdigest()
        await repository.accept_consent(token_hash(token), ConsentRecord(interview_id=interview.id, accepted_at=clock(), text_version=CONSENT_VERSION, ip_hash=digest))
        return {"room": f"/i/{token}/room"}

    @app.get("/i/{token}/room", response_class=HTMLResponse)
    async def room(token: str, request: Request):
        interview = await repository.by_token(token_hash(token))
        if interview.status == "active":
            await authorize(request, interview.id)
        elif interview.status != "consented" or clock() >= interview.expires_at:
            raise HTTPException(403, "Primero debés dar tu consentimiento.")
        return room_page(token, interview.id)

    @app.post("/i/{token}/start")
    async def start(token: str, request: Request):
        interview = await repository.by_token(token_hash(token))
        lock = locks.setdefault(interview.id, asyncio.Lock())
        async with lock:
            interview = await repository.by_token(token_hash(token))
            if interview.status == "active":
                await authorize(request, interview.id)
                _, snapshot = await get_engine(interview)
                if clock() >= snapshot.deadline:
                    raise HTTPException(410, "Tiempo de entrevista agotado.")
                return {"id": str(interview.id), "resumed": True, "decision": {"state": snapshot.state.model_dump(), "text": "Podés continuar con la entrevista."}}
            role = roles.get(interview.role_id)
            if role is None or role.version != interview.role_version:
                raise HTTPException(409, "Rol no disponible.")
            interview = await repository.claim_session(token_hash(token), clock())
            deadline = interview.started_at + timedelta(minutes=settings.interview_max_minutes)
            engine = engine_factory()
            try:
                decision = await asyncio.wait_for(engine.start(role, interview.candidate), timeout=min(30, max(.01, (deadline - clock()).total_seconds())))
                await persist(interview, engine, decision, deadline)
                if not decision.end_session:
                    engines[interview.id] = engine
                    key = await repository.issue_session_key(interview.id, deadline + timedelta(hours=1))
            except Exception:
                current = await repository.get(interview.id)
                if current and current.status == "active":
                    await repository.finish(interview.id, clock(), aborted=True)
                raise
            response = JSONResponse({"id": str(interview.id), "decision": decision.model_dump(mode="json")})
            if not decision.end_session:
                response.set_cookie(cookie_name(interview.id), key, max_age=(settings.interview_max_minutes + 60) * 60, httponly=True, secure=origin.scheme == "https", samesite="strict", path="/")
            return response

    @app.post("/session/{interview_id}/turn")
    async def candidate_turn(interview_id: UUID, body: CandidateText, request: Request):
        await authorize(request, interview_id)
        async with locks.setdefault(interview_id, asyncio.Lock()):
            interview = await authorize(request, interview_id)
            engine, snapshot = await get_engine(interview)
            elapsed = max(0, (clock() - interview.started_at).total_seconds())
            if clock() >= snapshot.deadline:
                decision = await asyncio.wait_for(engine.on_event(EngineEvent(kind="deadline_reached", elapsed_seconds=elapsed)), timeout=2)
                if not decision.end_session:
                    raise StorageError("deadline must end session")
            else:
                role = roles[interview.role_id]
                competency = role.competencies[snapshot.state.competency_index].id if snapshot.state.phase == InterviewPhase.COMPETENCIES else None
                turn = Turn(speaker="candidate", text=body.text, ts_start=elapsed, ts_end=elapsed, phase=snapshot.state.phase, competency_id=competency)
                try:
                    decision = await asyncio.wait_for(engine.on_candidate_turn(turn), timeout=min(30, max(.01, (snapshot.deadline - clock()).total_seconds())))
                except TimeoutError:
                    engines.pop(interview.id, None)
                    raise HTTPException(504, "La respuesta tardó demasiado. Podés volver a intentar.")
                except Exception:
                    engines.pop(interview.id, None)
                    raise
            try:
                await persist(interview, engine, decision, snapshot.deadline)
            except Exception:
                engines.pop(interview.id, None)
                raise
            return decision.model_dump(mode="json")

    @app.post("/session/{interview_id}/finish")
    async def finish(interview_id: UUID, request: Request):
        await authorize(request, interview_id)
        async with locks.setdefault(interview_id, asyncio.Lock()):
            interview = await authorize(request, interview_id)
            try:
                engine, snapshot = await get_engine(interview)
                decision = await asyncio.wait_for(engine.on_event(EngineEvent(kind="candidate_end", elapsed_seconds=max(0, (clock() - interview.started_at).total_seconds()))), timeout=2)
                if not decision.end_session:
                    raise StorageError("candidate end must end session")
                await persist(interview, engine, decision, snapshot.deadline)
                return decision.model_dump(mode="json")
            except Exception:
                # A request to stop must not leave a failed/mutated engine resumable.
                # Preserve already committed evidence and close the storage record even
                # when the final engine event or progress write failed.
                current = await repository.get(interview_id)
                if current and current.status == "active":
                    await repository.finish(interview_id, clock(), aborted=True)
                raise HTTPException(503, "La entrevista finalizó por un problema técnico. El equipo humano podrá revisar las respuestas guardadas.") from None
            finally:
                engines.pop(interview_id, None)

    @app.post("/session/{interview_id}/survey")
    async def survey(interview_id: UUID, body: Survey, request: Request):
        await authorize(request, interview_id, finished=True)
        await repository.save_survey(interview_id, body.clarity, body.fairness, body.comment)
        return {"saved": True}

    @app.post("/session/{interview_id}/offer")
    async def offer(interview_id: UUID, request: Request):
        await authorize(request, interview_id)
        raise HTTPException(503, "Audio y video todavía no están disponibles; podés continuar en texto.")

    @app.get("/admin/interviews/{interview_id}/report", dependencies=[Depends(admin)])
    async def report(interview_id: UUID):
        value = await repository.get_report(interview_id)
        if not value:
            raise HTTPException(404, "Reporte aún no disponible.")
        return value.model_dump(mode="json")

    @app.post("/admin/interviews/{interview_id}/report", dependencies=[Depends(admin)])
    async def generate_report(interview_id: UUID):
        if report_factory is None:
            raise HTTPException(503, "Generación de reportes no configurada.")
        async with locks.setdefault(interview_id, asyncio.Lock()):
            interview = await repository.get(interview_id)
            if not interview or interview.status not in {"completed", "aborted"}:
                raise HTTPException(409, "La entrevista todavía no finalizó.")
            existing = await repository.get_report(interview_id)
            if existing:
                return existing.model_dump(mode="json")
            role = roles.get(interview.role_id)
            if not role or role.version != interview.role_version:
                raise HTTPException(409, "Versión del rol no disponible.")
            result = await asyncio.wait_for(report_factory(interview, role, await repository.transcript(interview_id)), timeout=120)
            if result.interview_id != interview_id or {item.competency_id for item in result.scores} != {item.id for item in role.competencies}:
                raise StorageError("report does not match interview and rubric")
            await repository.save_report(result)
            return result.model_dump(mode="json")

    @app.delete("/admin/interviews/{interview_id}", dependencies=[Depends(admin)], status_code=204)
    async def delete(interview_id: UUID):
        async with locks.setdefault(interview_id, asyncio.Lock()):
            await repository.delete(interview_id)
            engines.pop(interview_id, None)
        return Response(status_code=204)

    @app.get("/assets/consent.js")
    async def consent_script():
        return Response(CONSENT_JS, media_type="application/javascript")

    @app.get("/assets/room.js")
    async def room_script():
        return Response(ROOM_JS, media_type="application/javascript")

    return app
