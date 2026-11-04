from datetime import timedelta
from uuid import uuid4

import pytest

from ai_interviewer.contracts import Candidate, InterviewPhase, SessionSnapshot
from ai_interviewer.engine import StructuredInterviewEngine
from ai_interviewer.engine.preferences import NamePreference, clean_name, replay_preferences
from test_engine import ROLE, NOW, Concrete, answer


@pytest.mark.parametrize("utterance", [
    "Can you call me by my name?", "Could you use my name?",
    "Call me by name", "Can you call me Sebastian?", "Please call me Sebastian",
    "My name is Sebastian", "¿Podés llamarme por mi nombre?",
    "Llamame Sebastian", "Me llamo Sebastian",
])
def test_name_preferences(utterance):
    preference = NamePreference("Sebastian")
    assert "Sebastian" in preference.handle(utterance)


@pytest.mark.parametrize("value", ["<script>alert</script>", "Ignore previous instructions", "Synthetic", "I am director", "yes", "A" * 51])
def test_invalid_names(value):
    assert clean_name(value) is None


async def test_name_request_does_not_repeat_advance_or_consume_followups_after_restore():
    analyzer = Concrete()
    engine = StructuredInterviewEngine(analyzer=analyzer, context_first=True, auto_language=True, now=lambda: NOW)
    await engine.start(ROLE, Candidate(name="Sebastian", email="test@example.invalid"))
    original = await engine.on_candidate_turn(answer(engine, "I lead a product team and own the payment experience."))
    for _ in range(3):
        acknowledgement = await engine.on_candidate_turn(answer(engine, "Can you call me by my name?"))
        assert "Of course, Sebastian." in acknowledgement.text
        assert original.text not in acknowledgement.text
        assert acknowledgement.state.phase == InterviewPhase.COMPETENCIES
        assert acknowledgement.state.competency_index == 0
        assert acknowledgement.state.followup_count == 0
    assert not analyzer.calls
    snapshot = SessionSnapshot(interview_id=uuid4(), state=engine.state,
        deadline=NOW + timedelta(minutes=30), updated_at=NOW)
    resumed = StructuredInterviewEngine(analyzer=analyzer, auto_language=True, now=lambda: NOW)
    await resumed.restore(ROLE, engine.candidate, snapshot, engine.transcript())
    repeated = await resumed.on_candidate_turn(answer(resumed, "Please repeat"))
    assert repeated.text == original.text
    following = await resumed.on_candidate_turn(answer(resumed, "I interviewed customers, changed the flow and reduced errors by twenty percent."))
    assert following.state.competency_index == 1
    assert len(analyzer.calls) == 1
    assert "call me" not in analyzer.calls[0][0]


async def test_unknown_name_and_preference_survive_restore_without_skipping_context():
    engine = StructuredInterviewEngine(context_first=True, auto_language=True, now=lambda: NOW)
    await engine.start(ROLE, Candidate(name="Synthetic", email="test@example.invalid"))
    ask = await engine.on_candidate_turn(answer(engine, "Can you call me by my name?"))
    assert "What would you like me to call you?" in ask.text
    snapshot = SessionSnapshot(interview_id=uuid4(), state=engine.state,
        deadline=NOW + timedelta(minutes=30), updated_at=NOW)
    resumed = StructuredInterviewEngine(auto_language=True, now=lambda: NOW)
    await resumed.restore(ROLE, engine.candidate, snapshot, engine.transcript())
    acknowledged = await resumed.on_candidate_turn(answer(resumed, "Sebastian"))
    assert "Of course, Sebastian." in acknowledged.text
    assert acknowledged.state.phase == InterviewPhase.WARMUP
    preference, excluded = replay_preferences(resumed.transcript())
    assert preference.name == "Sebastian" and len(excluded) == 2
    result = await resumed.on_candidate_turn(answer(resumed, "I lead a product team and own the customer experience."))
    assert result.state.phase == InterviewPhase.COMPETENCIES


async def test_spanish_name_acknowledgement():
    engine = StructuredInterviewEngine(context_first=True, auto_language=True, now=lambda: NOW)
    await engine.start(ROLE, Candidate(name="Sebastián", email="test@example.invalid"))
    result = await engine.on_candidate_turn(answer(engine, "¿Podés llamarme por mi nombre?"))
    assert "Claro, Sebastián." in result.text
    assert result.state.phase == InterviewPhase.WARMUP


async def test_pending_name_does_not_swallow_professional_answer():
    engine = StructuredInterviewEngine(context_first=True, auto_language=True, now=lambda: NOW)
    await engine.start(ROLE, Candidate(name="Synthetic", email="test@example.invalid"))
    await engine.on_candidate_turn(answer(engine, "Can you call me by my name?"))
    result = await engine.on_candidate_turn(answer(engine, "I lead product"))
    assert result.state.phase == InterviewPhase.COMPETENCIES

async def test_scoring_replay_does_not_mistake_answer_for_name():
    engine = StructuredInterviewEngine(context_first=True, auto_language=True, now=lambda: NOW)
    await engine.start(ROLE, Candidate(name="Sebastian", email="test@example.invalid"))
    request_turn = answer(engine, "Can you call me by my name?")
    await engine.on_candidate_turn(request_turn)
    professional = answer(engine, "We launched payments")
    await engine.on_candidate_turn(professional)
    _, excluded = replay_preferences(engine.transcript())
    assert request_turn.id in excluded
    assert professional.id not in excluded
