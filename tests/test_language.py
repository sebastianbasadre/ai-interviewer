from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4
import pytest
from ai_interviewer.engine.language import detect_language, QUESTION_ENGLISH, ENGLISH
from ai_interviewer.engine import StructuredInterviewEngine, load_role
from ai_interviewer.contracts import Candidate, Turn, InterviewPhase, SessionSnapshot

ROLE = load_role(Path(__file__).resolve().parents[1] / "roles/pm_po.yaml")
NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)

@pytest.mark.parametrize("text,current,expected", [
    ("I lead a product team and work with engineering to deliver payment features.", "es", "en"),
    ("Soy directora de producto y trabajo con el equipo para resolver problemas de usuarios.", "en", "es"),
    ("Yes", "es", "es"), ("No", "en", "en"),
    ("Spanish please", "en", "es"), ("English please", "es", "en"),
    ("", "en", "en"), ("1234", "es", "es"),
])
def test_language_detection(text, current, expected):
    assert detect_language(text, current) == expected

async def test_bilingual_context_and_restore():
    engine = StructuredInterviewEngine(context_first=True, auto_language=True, now=lambda: NOW)
    first = await engine.start(ROLE, Candidate(name="Synthetic", email="test@example.invalid"))
    assert first.text.startswith("I am an AI interviewer")
    assert first.state.phase == InterviewPhase.WARMUP
    turn = Turn(speaker="candidate", text="Soy directora de producto y trabajo con un equipo de desarrollo.", phase=engine.state.phase, ts_start=0, ts_end=5)
    result = await engine.on_candidate_turn(turn)
    assert result.text == ROLE.competencies[0].questions[0].text
    snapshot = SessionSnapshot(interview_id=uuid4(), state=engine.state, deadline=NOW+timedelta(minutes=30), updated_at=NOW)
    resumed = StructuredInterviewEngine(auto_language=True, now=lambda: NOW)
    await resumed.restore(ROLE, engine.candidate, snapshot, engine.transcript())
    assert resumed.language == "es"
    turn = Turn(speaker="candidate", text="I interviewed customers and changed our payment flow based on their feedback.", phase=engine.state.phase, competency_id=ROLE.competencies[0].id, ts_start=5, ts_end=10)
    followup = await resumed.on_candidate_turn(turn)
    assert resumed.language == "en"
    assert followup.text.startswith("Could you give")

def test_all_role_questions_have_english_wording():
    assert all(q.id in QUESTION_ENGLISH for c in ROLE.competencies for q in c.questions)

async def test_language_preference_repeats_context_without_advancing():
    engine = StructuredInterviewEngine(context_first=True, auto_language=True, now=lambda: NOW)
    await engine.start(ROLE, Candidate(name="Synthetic", email="test@example.invalid"))
    result = await engine.on_candidate_turn(Turn(speaker="candidate", text="Spanish please", phase=engine.state.phase, ts_start=0, ts_end=2))
    assert result.state.phase == InterviewPhase.WARMUP
    assert "contexto profesional" in result.text
    assert result.flags == ["language_preference"]
