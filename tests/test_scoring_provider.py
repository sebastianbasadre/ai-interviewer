import json
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import SecretStr
import pytest

from ai_interviewer.engine import load_role
from ai_interviewer.engine.anthropic import CallBudget, ReservedCalls, ConversationModelError
from ai_interviewer.scoring.anthropic import AnthropicScoringModel
from ai_interviewer.scoring import InterviewScorer
from ai_interviewer.contracts import Turn, InterviewPhase

ROLE = load_role(Path("roles/pm_po.yaml"))


def score_response(request, *, bad_id=False):
    body = json.loads(request.content)
    payload = json.loads(body["messages"][0]["content"])
    scores = []
    for index, comp in enumerate(payload["role"]["competencies"]):
        turns = [turn for turn in payload["transcript"] if turn["competency_id"] == comp["id"]]
        enough = bool(turns) and index != 2
        scores.append({"competency_id": comp["id"], "score": 3 if enough else None,
            "evidence_turn_ids": [(str(uuid4()) if bad_id else turns[0]["id"])] if enough else [],
            "rationale": "Describe una decisión con evidencia y resultado." if enough else "Falta un ejemplo concreto que permita aplicar las anclas.",
            "insufficient_evidence": not enough})
    return httpx.Response(200, json={"stop_reason": "end_turn",
        "content": [{"type": "text", "text": json.dumps({"scores": scores})}]})


async def test_real_provider_boundary_three_runs_evidence_and_missing_competency(tmp_path):
    turns = [Turn(speaker="candidate", text="En un proyecto entrevisté usuarios y cambié el flujo; los errores bajaron un 20%.",
                  ts_start=i, ts_end=i+1, phase=InterviewPhase.COMPETENCIES, competency_id=comp.id)
             for i, comp in enumerate(ROLE.competencies)]
    calls = []
    def handler(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["model"] == "claude-opus-5-5" and payload["max_tokens"] == 4096
        assert payload["output_config"]["format"]["schema"]["additionalProperties"] is False
        return score_response(request)
    budget = CallBudget(tmp_path / "budget.sqlite3", 3)
    budget.reserve(3)
    model = AnthropicScoringModel(SecretStr("unit-test-key"), model="claude-opus-5-5",
                                 budget=ReservedCalls(3), transport=httpx.MockTransport(handler))
    report = await InterviewScorer(model).score(uuid4(), ROLE, turns)
    assert len(calls) == 3 and "mock_scoring" not in report.flags
    assert report.scores[2].score is None and report.scores[2].insufficient_evidence
    assert all(score.score == 3 and score.evidence_turn_ids for i, score in enumerate(report.scores) if i != 2)
    with pytest.raises(ConversationModelError):
        budget.reserve(3)


def test_report_reservation_is_atomic_when_fewer_than_three_calls_remain(tmp_path):
    budget = CallBudget(tmp_path / "budget.sqlite3", 5)
    budget.reserve(3)
    with pytest.raises(ConversationModelError):
        budget.reserve(3)
    # The failed reservation consumed nothing: the last two calls remain usable.
    budget.reserve(2)
    with pytest.raises(ConversationModelError):
        budget.reserve()


def test_score_range_is_validated_locally_even_with_permissive_provider_schema(tmp_path):
    model = AnthropicScoringModel(SecretStr("unit-test-key"), model="claude-opus-5-5",
                                 budget=ReservedCalls(1))
    scores = [{"competency_id": comp.id, "score": 6, "insufficient_evidence": False,
               "evidence_turn_ids": [str(uuid4())], "rationale": "Describe una decisión."}
              for comp in ROLE.competencies]
    with pytest.raises(ValueError):
        model.validate_result({"scores": scores})


async def test_provider_cannot_introduce_foreign_evidence(tmp_path):
    turn = Turn(speaker="candidate", text="Investigué un problema y observé menos errores.",
                ts_start=0, ts_end=1, phase=InterviewPhase.COMPETENCIES, competency_id=ROLE.competencies[0].id)
    model = AnthropicScoringModel(SecretStr("unit-test-key"), model="claude-opus-5-5",
        budget=CallBudget(tmp_path / "budget.sqlite3", 3),
        transport=httpx.MockTransport(lambda request: score_response(request, bad_id=True)))
    with pytest.raises(ValueError, match="evidence"):
        await InterviewScorer(model).score(uuid4(), ROLE, [turn])
