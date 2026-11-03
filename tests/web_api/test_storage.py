from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import asyncio

import pytest

from ai_interviewer.contracts import (
    Candidate, CompetencyScore, ConsentRecord, Interview, InterviewPhase,
    InterviewReport, InterviewState, RecordingChunk, SessionSnapshot, Turn,
)
from ai_interviewer.storage import SQLiteSessionStore, StorageError
from ai_interviewer.storage.sqlite import token_hash

NOW = datetime(2026, 11, 2, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    repository = SQLiteSessionStore(tmp_path)
    yield repository
    repository.close()


def invitation():
    return Interview(candidate=Candidate(name="Candidate", email="a@b.test"), role_id="pm_po", role_version="1", token_hash=token_hash(str(uuid4())), created_at=NOW, expires_at=NOW + timedelta(days=7))


async def active(store):
    interview = invitation()
    await store.create(interview)
    await store.accept_consent(interview.token_hash, ConsentRecord(interview_id=interview.id, accepted_at=NOW, text_version="v1", ip_hash="a" * 64))
    return await store.claim_session(interview.token_hash, NOW)


def snapshot(interview, elapsed=0):
    return SessionSnapshot(interview_id=interview.id, state=InterviewState(phase=InterviewPhase.WARMUP, elapsed_seconds=elapsed), deadline=NOW + timedelta(minutes=30), updated_at=NOW)


def turn():
    return Turn(speaker="candidate", text="Contenido profesional", ts_start=1, ts_end=2, phase=InterviewPhase.WARMUP)


def chunk():
    return RecordingChunk(speaker="candidate", sequence=0, ts_start=1, audio=b"\0\0", sample_rate=16000)


async def test_all_content_writes_require_consent_and_active_status(store):
    interview = invitation()
    await store.create(interview)
    for operation in [store.append_turn(interview.id, turn()), store.save_audio(interview.id, chunk()), store.save_snapshot(snapshot(interview))]:
        with pytest.raises(StorageError):
            await operation
    with pytest.raises(StorageError):
        await store.claim_session(interview.token_hash, NOW)
    assert await store.transcript(interview.id) == []
    assert not (store.root / str(interview.id)).exists()


async def test_atomic_single_use_claim_and_hash_only_credentials(store):
    interview = await active(store)
    with pytest.raises(StorageError):
        await store.claim_session(interview.token_hash, NOW)
    key = await store.issue_session_key(interview.id, NOW + timedelta(hours=1))
    assert len(key) >= 43
    assert (await store.authorize(interview.id, key, NOW)).id == interview.id
    with pytest.raises(StorageError):
        await store.authorize(interview.id, "wrong", NOW)
    with pytest.raises(StorageError):
        await store.authorize(interview.id, key, NOW + timedelta(hours=1))
    row = store._db.execute("SELECT key_hash FROM session_keys").fetchone()
    assert row[0] == token_hash(key)
    assert key.encode() not in (store.root / "interviews.sqlite3").read_bytes()


async def test_snapshot_deadline_cannot_extend_and_progress_is_atomic(store):
    interview = await active(store)
    first = snapshot(interview)
    await store.save_snapshot(first)
    with pytest.raises(StorageError):
        await store.save_snapshot(first.model_copy(update={"deadline": first.deadline + timedelta(minutes=1)}))
    original = turn()
    await store.save_progress(first, [original], ["injection_attempt"])
    assert await store.get_flags(interview.id) == ["injection_attempt"]
    assert await store.transcript(interview.id) == [original]
    with pytest.raises(StorageError):
        await store.save_progress(snapshot(interview, elapsed=20), [turn()], ["sensitive free text"])
    assert await store.transcript(interview.id) == [original]
    # Existing UUID with changed text rejects entire batch, including new turn/state.
    changed = original.model_copy(update={"text": "Changed"})
    with pytest.raises(StorageError):
        await store.save_progress(snapshot(interview, elapsed=20), [turn(), changed])
    assert (await store.get_snapshot(interview.id)).state.elapsed_seconds == 0
    assert await store.transcript(interview.id) == [original]


async def test_turn_retry_is_idempotent_and_cannot_cross_interviews(store):
    first, second = await active(store), await active(store)
    item = turn()
    await store.append_turn(first.id, item)
    await store.append_turn(first.id, item)
    assert len(await store.transcript(first.id)) == 1
    with pytest.raises(StorageError):
        await store.append_turn(second.id, item)
    await store.finish(first.id, NOW + timedelta(seconds=5))
    with pytest.raises(StorageError):
        await store.append_turn(first.id, turn())


async def test_audio_separate_files_duplicate_protection_and_full_delete(store):
    interview = await active(store)
    await store.append_turn(interview.id, turn())
    await store.save_audio(interview.id, chunk())
    folder = store.root / str(interview.id)
    assert (folder / "candidate-00000000.pcm").read_bytes() == b"\0\0"
    assert '"sample_rate": 16000' in (folder / "candidate-00000000.json").read_text()
    with pytest.raises(StorageError):
        await store.save_audio(interview.id, chunk())
    await store.delete(interview.id)
    assert not folder.exists()
    assert await store.get(interview.id) is None
    assert await store.transcript(interview.id) == []
    assert b"Contenido profesional" not in (store.root / "interviews.sqlite3").read_bytes()


async def test_symlink_directory_never_writes_or_deletes_outside_root(store, tmp_path):
    interview = await active(store)
    outside = tmp_path.parent / f"outside-{uuid4()}"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("keep")
    link = store.root / str(interview.id)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on platform")
    with pytest.raises(StorageError):
        await store.save_audio(interview.id, chunk())
    with pytest.raises(StorageError):
        await store.delete(interview.id)
    assert marker.read_text() == "keep"


async def test_retention_uses_close_time_and_deletes_all_personal_data(store):
    old = await active(store)
    fresh = await active(store)
    await store.save_audio(old.id, chunk())
    await store.finish(old.id, NOW + timedelta(minutes=1))
    await store.finish(fresh.id, NOW + timedelta(days=20))
    assert await store.purge_expired(NOW + timedelta(days=10)) == 1
    assert await store.get(old.id) is None
    assert await store.get(fresh.id) is not None
    assert not (store.root / str(old.id)).exists()


async def test_reports_only_finished_with_matching_role_and_existing_candidate_evidence(store):
    interview = await active(store)
    item = turn()
    await store.append_turn(interview.id, item)
    report = InterviewReport(interview_id=interview.id, role_id=interview.role_id, role_version=interview.role_version, generated_at=NOW, summary="Summary", recommendation="Revisión humana", scores=[CompetencyScore(competency_id=str(i), score=3, evidence_turn_ids=[item.id], rationale="Evidence", insufficient_evidence=False) for i in range(6)])
    with pytest.raises(StorageError):
        await store.save_report(report)
    await store.finish(interview.id, NOW + timedelta(minutes=1))
    with pytest.raises(StorageError):
        await store.save_report(report.model_copy(update={"role_version": "2"}))
    invalid = report.model_copy(update={"scores": [s.model_copy(update={"evidence_turn_ids": [uuid4()]}) for s in report.scores]})
    with pytest.raises(StorageError):
        await store.save_report(invalid)
    await store.save_report(report)
    assert await store.get_report(interview.id) == report
    await store.save_survey(interview.id, 4, 5, "Comment")
    await store.delete(interview.id)
    assert await store.get_report(interview.id) is None
    assert store._db.execute("SELECT COUNT(*) FROM surveys").fetchone()[0] == 0

async def test_replace_progress_rolls_back_undelivered_interviewer_turns(store):
    interview = await active(store)
    snap = snapshot(interview)
    candidate_turn = turn()
    interviewer_turn = Turn(speaker="interviewer", text="Next question?", ts_start=3, ts_end=4, phase=InterviewPhase.WARMUP)
    await store.save_progress(snap, [candidate_turn, interviewer_turn])
    assert len(await store.transcript(interview.id)) == 2

    # Roll back: supply only the delivered candidate turn; drop the undelivered interviewer turn.
    snap2 = snapshot(interview, elapsed=5)
    await store.replace_progress(snap2, [candidate_turn])
    assert await store.transcript(interview.id) == [candidate_turn]
    restored = await store.get_snapshot(interview.id)
    assert restored.state.elapsed_seconds == 5


async def test_replace_progress_refuses_to_discard_candidate_evidence(store):
    interview = await active(store)
    candidate_turn = turn()
    await store.save_progress(snapshot(interview), [candidate_turn])
    # Attempting to omit a persisted candidate turn must be rejected.
    with pytest.raises(StorageError):
        await store.replace_progress(snapshot(interview, elapsed=5), [])
    # Transcript must be unchanged after the rejected rollback.
    assert await store.transcript(interview.id) == [candidate_turn]


async def test_two_connections_cannot_claim_same_invitation(store):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    interview = invitation()
    await store.create(interview)
    await store.accept_consent(interview.token_hash, ConsentRecord(interview_id=interview.id, accepted_at=NOW, text_version="v1", ip_hash="a" * 64))
    second = SQLiteSessionStore(store.root)
    barrier = Barrier(2)

    def claim(repository):
        barrier.wait(timeout=5)
        try:
            asyncio.run(repository.claim_session(interview.token_hash, NOW))
            return True
        except StorageError:
            return False

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(claim, [store, second]))
        assert sorted(outcomes) == [False, True]
    finally:
        second.close()
