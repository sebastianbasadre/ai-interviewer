from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_interviewer.contracts import CompetencyScore, ConsentRecord, Interview, InterviewPhase, Turn, Candidate, EngineEvent, InterviewState, SessionSnapshot


def test_numeric_score_requires_evidence():
    with pytest.raises(ValidationError):
        CompetencyScore(competency_id="discovery", score=4, rationale="unsupported", insufficient_evidence=False)
    score = CompetencyScore(competency_id="discovery", score=4, evidence_turn_ids=[uuid4()], rationale="example", insufficient_evidence=False)
    assert score.score == 4


@pytest.mark.parametrize("score,insufficient", [(None, False), (3, True), (True, False), (6, False)])
def test_score_rejects_inconsistent_or_invalid_values(score, insufficient):
    with pytest.raises(ValidationError):
        CompetencyScore(competency_id="discovery", score=score, evidence_turn_ids=[uuid4()], rationale="x", insufficient_evidence=insufficient)


def test_insufficient_evidence_serializes_as_null():
    score = CompetencyScore(competency_id="discovery", rationale="No example", insufficient_evidence=True)
    assert score.model_dump()["score"] is None


def test_turn_requires_ordered_timestamps_and_competency():
    data = dict(speaker="candidate", text="example", ts_start=4, ts_end=2, phase=InterviewPhase.COMPETENCIES)
    with pytest.raises(ValidationError):
        Turn(**data)
    data.update(ts_end=5, competency_id="discovery")
    assert Turn(**data).ts_end == 5


def test_consent_requires_timezone_and_hash():
    with pytest.raises(ValidationError):
        ConsentRecord(interview_id=uuid4(), accepted_at=datetime(2026, 1, 1), text_version="1", ip_hash="a" * 64)


def test_interview_expiry_must_follow_creation():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        Interview(candidate=Candidate(name="Test", email="test@example.invalid"), role_id="pm", role_version="1", token_hash="a" * 64, created_at=now, expires_at=now - timedelta(days=1))


def test_engine_event_rejects_unknown_events_or_invalid_clock():
    with pytest.raises(ValidationError):
        EngineEvent(kind="skip_phase", elapsed_seconds=1)
    with pytest.raises(ValidationError):
        EngineEvent(kind="deadline_reached", elapsed_seconds=-1)
    assert EngineEvent(kind="silence_timeout", elapsed_seconds=20).kind == "silence_timeout"


def test_snapshot_roundtrip_preserves_resume_limits():
    now = datetime.now(timezone.utc)
    snapshot = SessionSnapshot(interview_id=uuid4(), state=InterviewState(phase=InterviewPhase.COMPETENCIES, competency_index=3, followup_count=2, elapsed_seconds=900), deadline=now + timedelta(minutes=10), updated_at=now)
    restored = SessionSnapshot.model_validate_json(snapshot.model_dump_json())
    assert restored.state.phase == InterviewPhase.COMPETENCIES
    assert restored.state.competency_index == 3
    assert restored.state.followup_count == 2
    assert restored.state.elapsed_seconds == 900
    assert restored.deadline == snapshot.deadline
