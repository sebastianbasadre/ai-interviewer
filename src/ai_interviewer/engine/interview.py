"""Deterministic interview progression with explicit offline and injectable LLM modes."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from ai_interviewer.contracts import (
    Candidate, EngineDecision, EngineEvent, InterviewPhase, InterviewState,
    RoleSpec, SessionSnapshot, Turn,
)
from ai_interviewer.engine.llm import AnswerAnalysis
from ai_interviewer.engine.safety import has_sensitive, is_injection, normalized, safe_text


class AnswerAnalyzer(Protocol):
    async def analyze(self, text: str, question: str) -> AnswerAnalysis: ...


class QuestionWriter(Protocol):
    async def write(self, base_question: str, phase: str, competency_id: str | None) -> str: ...


class OfflineAnswerAnalyzer:
    """Conservative, deterministic mock. Does not establish interview quality."""
    async def analyze(self, text: str, question: str) -> AnswerAnalysis:
        # Offline mode deliberately requests STAR clarification rather than pretending
        # keyword matching can establish concrete evidence or relevance.
        return AnswerAnalysis(concrete_example=False)


class StructuredInterviewEngine:
    def __init__(self, analyzer: AnswerAnalyzer | None = None,
                 question_writer: QuestionWriter | None = None, *, max_minutes: int = 30,
                 now: Callable[[], datetime] | None = None, llm_timeout: float = 5):
        if not 1 <= max_minutes <= 30:
            raise ValueError("max_minutes must be between 1 and 30")
        self.analyzer = analyzer or OfflineAnswerAnalyzer()
        self.question_writer = question_writer
        self.max_seconds = max_minutes * 60
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.llm_timeout = llm_timeout
        self.state = InterviewState()
        self.role: RoleSpec | None = None
        self.candidate: Candidate | None = None
        self._turns: list[Turn] = []
        self._deadline: datetime | None = None
        self._last_question = ""

    def transcript(self) -> list[Turn]:
        return [turn.model_copy(deep=True) for turn in self._turns]

    async def start(self, role: RoleSpec, candidate: Candidate) -> EngineDecision:
        if self.role is not None:
            raise RuntimeError("engine already started")
        self.role, self.candidate = role.model_copy(deep=True), candidate.model_copy(deep=True)
        self.state = InterviewState(phase=InterviewPhase.INTRO)
        self._deadline = self.now() + timedelta(seconds=self.max_seconds)
        return self._say("Soy un entrevistador de IA; esta entrevista se graba y la revisa una persona. ¿Podemos empezar?")

    async def restore(self, role: RoleSpec, candidate: Candidate, snapshot: SessionSnapshot,
                      turns: list[Turn]) -> None:
        # Caller must bind role/version/candidate and transcript to the authorized
        # Interview: SessionSnapshot intentionally carries no identity attributes.
        if self.role is not None:
            raise RuntimeError("engine already started")
        if snapshot.updated_at > self.now() or snapshot.updated_at >= snapshot.deadline:
            raise ValueError("invalid snapshot dates")
        if snapshot.deadline <= self.now():
            raise ValueError("session deadline expired")
        if snapshot.state.elapsed_seconds >= self.max_seconds:
            raise ValueError("session duration exceeded")
        if snapshot.state.phase == InterviewPhase.CONSENT_CHECK:
            raise ValueError("cannot restore unstarted interview")
        if len({turn.id for turn in turns}) != len(turns):
            raise ValueError("duplicate transcript turn")
        valid_ids = {item.id for item in role.competencies}
        if any(turn.competency_id is not None and turn.competency_id not in valid_ids for turn in turns):
            raise ValueError("unknown competency in transcript")
        if any(turn.ts_end > snapshot.state.elapsed_seconds for turn in turns):
            raise ValueError("transcript newer than snapshot")
        self.role, self.candidate = role.model_copy(deep=True), candidate.model_copy(deep=True)
        self.state = snapshot.state.model_copy(deep=True)
        self._turns = [turn.model_copy(deep=True) for turn in turns]
        self._deadline = snapshot.deadline
        self._last_question = next((turn.text for turn in reversed(turns) if turn.speaker == "interviewer"), "")

    def _require_started(self) -> RoleSpec:
        if self.role is None:
            raise RuntimeError("engine not started")
        return self.role

    def _competency_id(self) -> str | None:
        if self.state.phase == InterviewPhase.COMPETENCIES:
            return self._require_started().competencies[self.state.competency_index].id
        return None

    def _say(self, text: str, flags: list[str] | None = None) -> EngineDecision:
        self._last_question = text
        if text:
            self._turns.append(Turn(speaker="interviewer", text=text,
                ts_start=self.state.elapsed_seconds, ts_end=self.state.elapsed_seconds,
                phase=self.state.phase, competency_id=self._competency_id()))
        return EngineDecision(state=self.state.model_copy(deep=True), text=text,
                              flags=flags or [], end_session=self.state.phase == InterviewPhase.DONE)

    def _expired(self) -> bool:
        return self.state.elapsed_seconds >= self.max_seconds or (self._deadline is not None and self.now() >= self._deadline)

    def _finish(self, flag: str) -> EngineDecision:
        self.state = self.state.model_copy(update={"phase": InterviewPhase.DONE})
        return self._say("Gracias por tu tiempo; terminamos la entrevista. El equipo humano revisará las respuestas.", [flag])

    async def _question(self, base: str, flags: list[str] | None = None) -> EngineDecision:
        flags = list(flags or [])
        text = base
        if self.question_writer is not None:
            try:
                generated = await asyncio.wait_for(self.question_writer.write(base, self.state.phase.value, self._competency_id()), self.llm_timeout)
                sentences = re.split(r"(?<=[.!?])\s+", generated.strip())
                allowed = {question.text for question in self._require_started().competencies[self.state.competency_index].questions}
                # Pilot guardrail: model selects only G2-approved wording in the
                # current competency; free-form paraphrasing needs semantic evals.
                if generated.strip() not in allowed or not generated.strip() or len(generated) > 500 or len(sentences) > 2 or has_sensitive(generated) or is_injection(generated):
                    raise ValueError("unsafe or overlong generated question")
                text = generated.strip()
            except Exception:  # Provider failures degrade safely; cancellation still propagates.
                flags.append("question_fallback")
        return self._say(text, flags)

    async def _advance(self, flags: list[str] | None = None) -> EngineDecision:
        role = self._require_started()
        phase = self.state.phase
        if phase == InterviewPhase.INTRO:
            self.state = self.state.model_copy(update={"phase": InterviewPhase.WARMUP, "followup_count": 0})
            return self._say("Para ubicarnos, contame brevemente qué responsabilidades de producto tuviste en una experiencia reciente.", flags)
        if phase == InterviewPhase.WARMUP:
            self.state = self.state.model_copy(update={"phase": InterviewPhase.COMPETENCIES, "competency_index": 0, "followup_count": 0})
        elif phase == InterviewPhase.COMPETENCIES:
            if self.state.competency_index == len(role.competencies) - 1:
                self.state = self.state.model_copy(update={"phase": InterviewPhase.CANDIDATE_QUESTIONS, "followup_count": 0})
                return self._say("¿Qué te gustaría preguntarle al equipo sobre el rol o la empresa?", flags)
            self.state = self.state.model_copy(update={"competency_index": self.state.competency_index + 1, "followup_count": 0})
        elif phase == InterviewPhase.CANDIDATE_QUESTIONS:
            self.state = self.state.model_copy(update={"phase": InterviewPhase.CLOSING})
            return self._say("Gracias por compartir tu experiencia. El equipo humano revisará la entrevista y responderá las consultas pendientes.", flags)
        elif phase == InterviewPhase.CLOSING:
            return self._finish("completed")
        return await self._question(role.competencies[self.state.competency_index].questions[0].text, flags)

    def _phase_elapsed(self) -> float:
        matching = [turn.ts_start for turn in self._turns if turn.speaker == "interviewer"
                    and turn.phase == self.state.phase and turn.competency_id == self._competency_id()]
        return self.state.elapsed_seconds - min(matching, default=self.state.elapsed_seconds)

    async def _followup(self, text: str, flags: list[str]) -> EngineDecision:
        role = self._require_started()
        if self.state.followup_count >= role.max_followups:
            return await self._advance(flags + ["followup_limit"])
        self.state = self.state.model_copy(update={"followup_count": self.state.followup_count + 1})
        return self._say(text, flags)

    async def on_candidate_turn(self, turn: Turn) -> EngineDecision:
        role = self._require_started()
        if self.state.phase == InterviewPhase.DONE:
            raise RuntimeError("interview already ended")
        if turn.speaker != "candidate" or turn.phase != self.state.phase or turn.competency_id != self._competency_id():
            raise ValueError("turn does not belong to current phase")
        if turn.ts_start < self.state.elapsed_seconds or any(existing.id == turn.id for existing in self._turns):
            raise ValueError("stale or duplicate turn")
        self.state = self.state.model_copy(update={"elapsed_seconds": turn.ts_end})
        self._turns.append(turn.model_copy(deep=True))
        if self._expired():
            return self._finish("duration_limit")
        text = normalized(turn.text).strip(" .!¿?¡")
        if re.search(r"\b(quiero terminar|terminemos|prefiero terminar|no quiero seguir|stop interview|end the interview|i want to stop)\b", text):
            return self._finish("candidate_end")
        injection = is_injection(turn.text)
        sensitive = has_sensitive(turn.text)
        flags = (["injection_attempt"] if injection else []) + (["sensitive_data_excluded"] if sensitive else [])
        phase_limit = 180 if self.state.phase == InterviewPhase.COMPETENCIES else 90
        if self._phase_elapsed() >= phase_limit:
            return await self._advance(flags + ["phase_time_limit"])
        if re.search(r"\b(repeti|repetis|repetir|repeat|no entendi|podes repetir)\b", text) and not injection:
            return await self._followup(self._last_question, flags + ["repeat_requested"])
        if self.state.phase == InterviewPhase.CANDIDATE_QUESTIONS:
            if text in {"no", "ninguna", "no gracias", "no tengo preguntas", "none", "no questions"}:
                return await self._advance(flags)
            # Exact confirmed keys only; no generation or fuzzy company facts.
            answer = role.company_info.get(text)
            return await self._followup(answer or "Esa información la va a responder el equipo humano. ¿Tenés otra consulta?", flags)
        if self.state.phase != InterviewPhase.COMPETENCIES:
            return await self._advance(flags)
        if injection:
            return await self._followup("Sigamos con tu experiencia profesional; contame un caso concreto relacionado con la pregunta.", flags)
        cleaned = safe_text(turn.text)
        if not cleaned:
            return await self._followup("Volvamos al trabajo de producto; contame una situación concreta, qué hiciste y qué resultado observaste.", flags)
        try:
            analysis = await asyncio.wait_for(self.analyzer.analyze(cleaned, self._last_question), self.llm_timeout)
            if not isinstance(analysis, AnswerAnalysis):
                raise ValueError("invalid analyzer response")
        except Exception:  # Provider failures degrade safely; cancellation still propagates.
            analysis = AnswerAnalysis()
            flags.append("analysis_fallback")
        if analysis.request == "end":
            return self._finish("candidate_end")
        if analysis.injection_attempt:
            flags.append("injection_attempt")
            return await self._followup("Sigamos con un ejemplo de tu experiencia profesional relacionado con la pregunta.", flags)
        if analysis.request == "repeat":
            return await self._followup(self._last_question, flags + ["repeat_requested"])
        if not analysis.on_topic:
            return await self._followup("Volvamos a la pregunta; elegí una situación concreta vinculada con esa decisión de producto.", flags + ["off_topic"])
        if not analysis.concrete_example:
            return await self._followup("¿Podés darme un ejemplo concreto con la situación, qué hiciste vos y qué resultado o aprendizaje hubo?", flags + ["star_followup"])
        return await self._advance(flags)

    async def on_event(self, event: EngineEvent) -> EngineDecision:
        self._require_started()
        if self.state.phase == InterviewPhase.DONE:
            return EngineDecision(state=self.state, text="", end_session=True)
        if event.elapsed_seconds < self.state.elapsed_seconds:
            raise ValueError("event precedes current state")
        self.state = self.state.model_copy(update={"elapsed_seconds": event.elapsed_seconds})
        if event.kind == "candidate_end":
            return self._finish("candidate_end")
        if event.kind == "deadline_reached" or self._expired():
            return self._finish("duration_limit")
        if self._phase_elapsed() >= (180 if self.state.phase == InterviewPhase.COMPETENCIES else 90):
            return await self._advance(["phase_time_limit"])
        return await self._followup(self._last_question or "¿Seguís ahí?", ["silence_timeout"])
