"""Shared boundaries. No provider SDK imports or network operations belong here."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InterviewPhase(StrEnum):
    CONSENT_CHECK = "consent_check"
    INTRO = "intro"
    WARMUP = "warmup"
    COMPETENCIES = "competencies"
    CANDIDATE_QUESTIONS = "candidate_questions"
    CLOSING = "closing"
    DONE = "done"


class RubricAnchor(Contract):
    score: Literal[1, 3, 5]
    description: str = Field(min_length=1)


class Question(Contract):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    followup_criteria: list[str] = Field(default_factory=list)


class Competency(Contract):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    questions: list[Question] = Field(min_length=2, max_length=3)
    anchors: list[RubricAnchor] = Field(min_length=3, max_length=3)
    transversal: bool = False

    @model_validator(mode="after")
    def validate_rubric(self) -> Competency:
        if {anchor.score for anchor in self.anchors} != {1, 3, 5}:
            raise ValueError("rubric must contain distinct 1/3/5 anchors")
        if len({question.id for question in self.questions}) != len(self.questions):
            raise ValueError("question IDs must be unique within a competency")
        return self


class RoleSpec(Contract):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    competencies: list[Competency] = Field(min_length=6, max_length=6)
    company_info: dict[str, str] = Field(default_factory=dict)
    target_minutes: int = Field(default=25, ge=20, le=25)
    max_followups: int = Field(default=2, ge=0, le=2)

    @model_validator(mode="after")
    def unique_competencies(self) -> RoleSpec:
        if len({item.id for item in self.competencies}) != len(self.competencies):
            raise ValueError("competency IDs must be unique")
        return self


class Candidate(Contract):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)


class ConsentRecord(Contract):
    interview_id: UUID
    accepted_at: AwareDatetime
    text_version: str = Field(min_length=1)
    ip_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class Turn(Contract):
    id: UUID = Field(default_factory=uuid4)
    speaker: Literal["candidate", "interviewer"]
    text: str = Field(min_length=1)
    # Seconds relative to interview start, on the same monotonic clock.
    ts_start: float = Field(ge=0, allow_inf_nan=False)
    ts_end: float = Field(ge=0, allow_inf_nan=False)
    phase: InterviewPhase
    competency_id: str | None = None

    @model_validator(mode="after")
    def ordered_time(self) -> Turn:
        if self.ts_end < self.ts_start:
            raise ValueError("turn end precedes start")
        if self.phase == InterviewPhase.COMPETENCIES and not self.competency_id:
            raise ValueError("competency phase requires competency_id")
        return self


class InterviewState(Contract):
    phase: InterviewPhase = InterviewPhase.CONSENT_CHECK
    competency_index: int = Field(default=0, ge=0, le=5)
    followup_count: int = Field(default=0, ge=0, le=2)
    elapsed_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)


class SessionSnapshot(Contract):
    """Persist before emitting the corresponding decision; resume within original deadline."""
    interview_id: UUID
    state: InterviewState
    deadline: AwareDatetime
    updated_at: AwareDatetime


class EngineEvent(Contract):
    kind: Literal["silence_timeout", "deadline_reached", "candidate_end"]
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)


class EngineDecision(Contract):
    state: InterviewState
    text: str
    flags: list[str] = Field(default_factory=list)
    end_session: bool = False

    @model_validator(mode="after")
    def ended_state(self) -> EngineDecision:
        if self.end_session != (self.state.phase == InterviewPhase.DONE):
            raise ValueError("end_session must match done phase")
        return self


class InterviewEngine(Protocol):
    """One engine instance per session; caller verifies consent before start."""
    async def start(self, role: RoleSpec, candidate: Candidate) -> EngineDecision: ...
    async def on_candidate_turn(self, turn: Turn) -> EngineDecision: ...
    async def on_event(self, event: EngineEvent) -> EngineDecision:
        """Silence repeats/rephrases; deadline/end terminate without another LLM call."""
        ...
    async def restore(self, role: RoleSpec, candidate: Candidate, snapshot: SessionSnapshot, turns: list[Turn]) -> None:
        """Restore state without emitting speech; caller validates credential and deadline."""
        ...
    def transcript(self) -> list[Turn]: ...


class InterviewEngineFactory(Protocol):
    """Return a fresh, unstarted engine with the same provider configuration.

    The coordinator serializes operations and retains the last delivered state.
    If speech onset invalidates an awaited response before text delivery, persist
    the real candidate turn, discard the mutated engine, and restore a fresh one
    with the last delivered phase/competency/followup state, original deadline,
    and committed transcript plus that candidate turn. Advance only elapsed time.
    Never persist or restore the generated but undelivered interviewer question.
    Rebuilding must not invoke providers or emit speech. Expired deadlines close
    the session without creating a new engine/provider operation.
    """
    def __call__(self) -> InterviewEngine: ...


class CompetencyScore(Contract):
    competency_id: str
    score: int | None = Field(default=None, ge=1, le=5, strict=True)
    evidence_turn_ids: list[UUID] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    insufficient_evidence: bool
    dispersion: float = Field(default=0, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def evidence_required(self) -> CompetencyScore:
        if self.insufficient_evidence != (self.score is None):
            raise ValueError("missing score must mean insufficient evidence")
        if self.score is not None and not self.evidence_turn_ids:
            raise ValueError("numeric score requires textual evidence")
        return self


class InterviewReport(Contract):
    interview_id: UUID
    role_id: str
    role_version: str
    generated_at: AwareDatetime
    scores: list[CompetencyScore] = Field(min_length=6, max_length=6)
    summary: str
    recommendation: str
    flags: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    scoring_runs: Literal[3] = 3

    @model_validator(mode="after")
    def unique_scores(self) -> InterviewReport:
        if len({item.competency_id for item in self.scores}) != len(self.scores):
            raise ValueError("report must score distinct competencies")
        return self


class Interview(Contract):
    id: UUID = Field(default_factory=uuid4)
    candidate: Candidate
    role_id: str
    role_version: str
    token_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: AwareDatetime
    expires_at: AwareDatetime
    status: Literal["invited", "consented", "active", "completed", "aborted"] = "invited"
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def ordered_dates(self) -> Interview:
        if self.expires_at <= self.created_at:
            raise ValueError("expiry must follow creation")
        if self.ended_at and (not self.started_at or self.ended_at < self.started_at):
            raise ValueError("invalid session end")
        return self


class RecordingChunk(Contract):
    speaker: Literal["candidate", "interviewer"]
    sequence: int = Field(ge=0)
    ts_start: float = Field(ge=0, allow_inf_nan=False)
    # Raw bytes are never included in logs or provider prompts.
    audio: bytes = Field(repr=False, exclude=True)
    sample_rate: int = Field(gt=0)
    channels: Literal[1, 2] = 1


class SessionStore(Protocol):
    """Implementations enforce consent, atomic token use and interview ownership."""
    async def create(self, interview: Interview) -> None: ...
    async def get(self, interview_id: UUID) -> Interview | None: ...
    async def accept_consent(self, token_hash: str, consent: ConsentRecord) -> Interview: ...
    async def claim_session(self, token_hash: str, now: datetime) -> Interview: ...
    async def save_snapshot(self, snapshot: SessionSnapshot) -> None: ...
    async def replace_progress(self, snapshot: SessionSnapshot, turns: list[Turn]) -> None:
        """Atomic rollback of output not yet accepted by the text enqueue boundary.

        Require active consented ownership and unchanged original deadline. Keep
        every persisted candidate turn ID/body and prior delivered transcript;
        only the coordinator's undelivered interviewer turns may be removed.
        Do not modify recordings, reports, or other interviews. The coordinator
        supplies the complete committed transcript plus real pending input.
        """
        ...
    async def get_snapshot(self, interview_id: UUID) -> SessionSnapshot | None: ...
    async def finish(self, interview_id: UUID, ended_at: datetime, *, aborted: bool = False) -> None: ...
    async def append_turn(self, interview_id: UUID, turn: Turn) -> None: ...
    async def transcript(self, interview_id: UUID) -> list[Turn]: ...
    async def save_audio(self, interview_id: UUID, chunk: RecordingChunk) -> None: ...
    async def save_report(self, report: InterviewReport) -> None: ...
    async def get_report(self, interview_id: UUID) -> InterviewReport | None: ...
    async def delete(self, interview_id: UUID) -> None: ...
    async def purge_expired(self, before: datetime) -> int: ...


class AvatarService(Protocol):
    """Provider adapters are owned by pipeline; mock implements the same lifecycle."""
    async def start(self, interview_id: UUID) -> None: ...
    async def send_audio(self, chunk: RecordingChunk) -> None: ...
    async def interrupt(self) -> None: ...
    async def close(self) -> None: ...
