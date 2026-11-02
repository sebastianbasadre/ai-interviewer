from __future__ import annotations

from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ai_interviewer.contracts import EngineDecision, InterviewPhase, RoleSpec, Turn


class Persona(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    description: str
    expected_scores: dict[str, int | None]
    default_answer: str
    competency_answers: dict[str, str] = Field(default_factory=dict)
    candidate_question: str = "No tengo preguntas"
    tags: list[str] = Field(default_factory=list)
    response_seconds: float = Field(default=15, gt=0, le=180)
    missing_example: bool = False
    sensitive_canaries: list[str] = Field(default_factory=list)


def load_personas(directory: str | Path, role: RoleSpec) -> list[Persona]:
    personas = []
    ids = {competency.id for competency in role.competencies}
    for path in sorted(Path(directory).glob("*.yaml")):
        persona = Persona.model_validate(yaml.safe_load(path.read_text(encoding="utf-8-sig")))
        if set(persona.expected_scores) != ids or not set(persona.competency_answers) <= ids:
            raise ValueError(f"persona {persona.id}: competency IDs do not match role")
        if any(value is not None and (type(value) is not int or not 1 <= value <= 5)
               for value in persona.expected_scores.values()):
            raise ValueError(f"persona {persona.id}: invalid expected score")
        personas.append(persona)
    if len({persona.id for persona in personas}) != len(personas):
        raise ValueError("duplicate persona IDs")
    return personas


class Answer(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    seconds: float = Field(default=15, gt=0, le=180)


class CandidateResponder(Protocol):
    async def answer(self, decision: EngineDecision, role: RoleSpec, history: list[Turn]) -> Answer: ...


class ScriptedCandidate:
    """Fixed fixtures exercise code paths; they do not simulate a language model."""
    def __init__(self, persona: Persona):
        self.persona = persona

    async def answer(self, decision: EngineDecision, role: RoleSpec, history: list[Turn]) -> Answer:
        phase = decision.state.phase
        if phase == InterviewPhase.INTRO:
            return Answer(text="Sí, podemos empezar.", seconds=1)
        if phase == InterviewPhase.WARMUP:
            return Answer(text="Trabajé en un equipo de producto digital y colaboré con diseño y desarrollo.", seconds=10)
        if phase == InterviewPhase.CANDIDATE_QUESTIONS:
            return Answer(text=self.persona.candidate_question, seconds=5)
        if phase == InterviewPhase.CLOSING:
            return Answer(text="Gracias.", seconds=1)
        competency = role.competencies[decision.state.competency_index].id
        return Answer(text=self.persona.competency_answers.get(competency, self.persona.default_answer),
                      seconds=self.persona.response_seconds)
