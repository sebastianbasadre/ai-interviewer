"""Consent-gated persistence; all mutations use short SQLite transactions.

The single-process pilot calls these async methods without internal suspension, so each
transaction is atomic with respect to the event loop. A lock also protects threaded callers.
Audio files are raw PCM with a JSON sidecar; the pipeline owns encoding/container conversion.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import UUID

from ai_interviewer.contracts import (
    ConsentRecord, Interview, InterviewReport, RecordingChunk, SessionSnapshot, Turn,
)


class StorageError(Exception):
    """A safe, content-free storage error."""


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SQLiteSessionStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir).absolute()
        if self.root.is_symlink():
            raise StorageError("data directory cannot be a symbolic link")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = self.root.resolve()
        database = self.root / "interviews.sqlite3"
        if database.is_symlink():
            raise StorageError("database cannot be a symbolic link")
        self._db = sqlite3.connect(database, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = RLock()
        self._db.executescript("""
            PRAGMA foreign_keys=ON;
            PRAGMA secure_delete=ON;
            CREATE TABLE IF NOT EXISTS interviews (
                id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS consent (
                interview_id TEXT PRIMARY KEY REFERENCES interviews(id) ON DELETE CASCADE,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turns (
                id TEXT PRIMARY KEY,
                interview_id TEXT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                interview_id TEXT PRIMARY KEY REFERENCES interviews(id) ON DELETE CASCADE,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                interview_id TEXT PRIMARY KEY REFERENCES interviews(id) ON DELETE CASCADE,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS report_states (
                interview_id TEXT PRIMARY KEY REFERENCES interviews(id) ON DELETE CASCADE,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS session_keys (
                interview_id TEXT PRIMARY KEY REFERENCES interviews(id) ON DELETE CASCADE,
                key_hash TEXT NOT NULL, expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS surveys (
                interview_id TEXT PRIMARY KEY REFERENCES interviews(id) ON DELETE CASCADE,
                body TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS flags (
                interview_id TEXT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
                value TEXT NOT NULL, PRIMARY KEY(interview_id, value)
            );
        """)
        database.chmod(0o600)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _get(self, interview_id: UUID) -> Interview:
        row = self._db.execute("SELECT body FROM interviews WHERE id=?", (str(interview_id),)).fetchone()
        if not row:
            raise StorageError("interview unavailable")
        return Interview.model_validate_json(row["body"])

    def _by_token(self, digest: str) -> Interview:
        row = self._db.execute("SELECT body FROM interviews WHERE token_hash=?", (digest,)).fetchone()
        if not row:
            raise StorageError("invitation unavailable")
        return Interview.model_validate_json(row["body"])

    def _write_interview(self, interview: Interview) -> None:
        self._db.execute("UPDATE interviews SET body=? WHERE id=?", (interview.model_dump_json(), str(interview.id)))

    def _consented(self, interview_id: UUID, *, active: bool = False) -> Interview:
        interview = self._get(interview_id)
        consent = self._db.execute("SELECT 1 FROM consent WHERE interview_id=?", (str(interview_id),)).fetchone()
        if not consent or (active and interview.status != "active"):
            raise StorageError("consented active interview required" if active else "consent required")
        return interview

    def _directory(self, interview_id: UUID, *, create: bool = False) -> Path:
        path = self.root / str(UUID(str(interview_id)))
        if path.is_symlink() or path.resolve().parent != self.root:
            raise StorageError("unsafe interview directory")
        if create:
            path.mkdir(mode=0o700, exist_ok=True)
        return path

    async def create(self, interview: Interview) -> None:
        if interview.status != "invited" or interview.started_at or interview.ended_at:
            raise StorageError("new interview must be invited")
        with self._lock, self._db:
            self._db.execute("INSERT INTO interviews VALUES(?,?,?)", (str(interview.id), interview.token_hash, interview.model_dump_json()))

    async def get(self, interview_id: UUID) -> Interview | None:
        with self._lock:
            try:
                return self._get(interview_id)
            except StorageError:
                return None

    async def by_token(self, digest: str) -> Interview:
        with self._lock:
            return self._by_token(digest)

    async def active(self) -> list[Interview]:
        with self._lock:
            rows = self._db.execute("SELECT body FROM interviews").fetchall()
            return [item for row in rows if (item := Interview.model_validate_json(row["body"])).status == "active"]

    async def accept_consent(self, token_hash: str, consent: ConsentRecord) -> Interview:
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                interview = self._by_token(token_hash)
                if interview.id != consent.interview_id or interview.status != "invited" or consent.accepted_at >= interview.expires_at:
                    raise StorageError("invitation unavailable")
                self._db.execute("INSERT INTO consent VALUES(?,?)", (str(interview.id), consent.model_dump_json()))
                interview = interview.model_copy(update={"status": "consented"})
                self._write_interview(interview)
                self._db.execute("COMMIT")
                return interview
            except Exception:
                try:
                    self._db.execute("ROLLBACK")
                except Exception:
                    pass  # BEGIN may not have acquired a transaction; suppress secondary error.
                raise

    async def claim_session(self, token_hash: str, now: datetime) -> Interview:
        with self._lock:
            # Explicit write transaction prevents two processes claiming the same invitation.
            try:
                self._db.execute("BEGIN IMMEDIATE")
                interview = self._by_token(token_hash)
                if interview.status != "consented" or now >= interview.expires_at:
                    raise StorageError("invitation unavailable")
                self._consented(interview.id)
                interview = interview.model_copy(update={"status": "active", "started_at": now})
                self._write_interview(interview)
                self._db.execute("COMMIT")
                return interview
            except Exception:
                try:
                    self._db.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    async def has_consent_version(self, interview_id: UUID, version: str) -> bool:
        with self._lock:
            row = self._db.execute("SELECT body FROM consent WHERE interview_id=?", (str(interview_id),)).fetchone()
            return bool(row and ConsentRecord.model_validate_json(row["body"]).text_version == version)

    async def issue_session_key(self, interview_id: UUID, expires_at: datetime) -> str:
        with self._lock, self._db:
            self._consented(interview_id, active=True)
            key = secrets.token_urlsafe(32)
            self._db.execute("INSERT OR REPLACE INTO session_keys VALUES(?,?,?)", (str(interview_id), token_hash(key), expires_at.isoformat()))
            return key

    async def authorize(self, interview_id: UUID, key: str, now: datetime, *, allow_finished: bool = False) -> Interview:
        with self._lock:
            row = self._db.execute("SELECT key_hash, expires_at FROM session_keys WHERE interview_id=?", (str(interview_id),)).fetchone()
            if not row or now >= datetime.fromisoformat(row["expires_at"]) or not secrets.compare_digest(row["key_hash"], token_hash(key)):
                raise StorageError("session unavailable")
            interview = self._consented(interview_id)
            allowed = {"active", "completed", "aborted"} if allow_finished else {"active"}
            if interview.status not in allowed:
                raise StorageError("session unavailable")
            return interview

    async def save_snapshot(self, snapshot: SessionSnapshot) -> None:
        with self._lock, self._db:
            self._save_snapshot(snapshot)

    def _save_snapshot(self, snapshot: SessionSnapshot) -> None:
        interview = self._consented(snapshot.interview_id, active=True)
        existing = self._db.execute("SELECT body FROM snapshots WHERE interview_id=?", (str(snapshot.interview_id),)).fetchone()
        if not interview.started_at < snapshot.deadline <= interview.started_at + timedelta(minutes=30):
            raise StorageError("invalid session deadline")
        if existing and SessionSnapshot.model_validate_json(existing["body"]).deadline != snapshot.deadline:
            raise StorageError("session deadline cannot change")
        self._db.execute("INSERT OR REPLACE INTO snapshots VALUES(?,?)", (str(snapshot.interview_id), snapshot.model_dump_json()))

    async def save_progress(self, snapshot: SessionSnapshot, turns: list[Turn], flags: list[str] | None = None) -> None:
        """Commit transcript and decision state together before exposing speech/text."""
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._save_snapshot(snapshot)
                for turn in turns:
                    self._append_turn(snapshot.interview_id, turn)
                for flag in flags or []:
                    if not re.fullmatch(r"[a-z0-9_]{1,80}", flag):
                        raise StorageError("invalid technical flag")
                    self._db.execute("INSERT OR IGNORE INTO flags VALUES(?,?)", (str(snapshot.interview_id), flag))
                self._db.execute("COMMIT")
            except Exception:
                try:
                    self._db.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    async def replace_progress(self, snapshot: SessionSnapshot, turns: list[Turn]) -> None:
        """Atomic rollback: discard undelivered interviewer turns, restore from checkpoint.

        The supplied turns are the complete committed transcript after rollback. Every
        candidate turn that was previously persisted must appear in turns; only
        undelivered interviewer turns may be absent. Recordings, reports, flags, and
        other interviews are not modified.
        """
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                # Validate ownership and deadline consistency first.
                self._save_snapshot(snapshot)
                # Guard: every previously persisted candidate turn must survive the rollback.
                existing_rows = self._db.execute(
                    "SELECT body FROM turns WHERE interview_id=?", (str(snapshot.interview_id),)
                ).fetchall()
                existing_candidate_ids = set()
                for row in existing_rows:
                    t = Turn.model_validate_json(row["body"])
                    if t.speaker == "candidate":
                        existing_candidate_ids.add(t.id)
                supplied_candidate_ids = {t.id for t in turns if t.speaker == "candidate"}
                if not existing_candidate_ids.issubset(supplied_candidate_ids):
                    raise StorageError("replace_progress would discard candidate evidence")
                # Replace turns atomically.
                self._db.execute("DELETE FROM turns WHERE interview_id=?", (str(snapshot.interview_id),))
                for turn in turns:
                    self._db.execute("INSERT INTO turns VALUES(?,?,?)", (str(turn.id), str(snapshot.interview_id), turn.model_dump_json()))
                self._db.execute("COMMIT")
            except Exception:
                try:
                    self._db.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    async def get_flags(self, interview_id: UUID) -> list[str]:
        with self._lock:
            return [row[0] for row in self._db.execute("SELECT value FROM flags WHERE interview_id=? ORDER BY value", (str(interview_id),)).fetchall()]

    async def get_snapshot(self, interview_id: UUID) -> SessionSnapshot | None:
        with self._lock:
            row = self._db.execute("SELECT body FROM snapshots WHERE interview_id=?", (str(interview_id),)).fetchone()
            return SessionSnapshot.model_validate_json(row["body"]) if row else None

    async def finish(self, interview_id: UUID, ended_at: datetime, *, aborted: bool = False) -> None:
        with self._lock, self._db:
            interview = self._consented(interview_id, active=True)
            if ended_at < interview.started_at:
                raise StorageError("invalid end time")
            self._write_interview(interview.model_copy(update={"ended_at": ended_at, "status": "aborted" if aborted else "completed"}))

    async def append_turn(self, interview_id: UUID, turn: Turn) -> None:
        with self._lock, self._db:
            self._append_turn(interview_id, turn)

    def _append_turn(self, interview_id: UUID, turn: Turn) -> None:
        self._consented(interview_id, active=True)
        existing = self._db.execute("SELECT interview_id, body FROM turns WHERE id=?", (str(turn.id),)).fetchone()
        if existing:
            if existing["interview_id"] != str(interview_id) or existing["body"] != turn.model_dump_json():
                raise StorageError("turn identity conflict")
            return  # Idempotent persistence after retry/reconnect.
        self._db.execute("INSERT INTO turns VALUES(?,?,?)", (str(turn.id), str(interview_id), turn.model_dump_json()))

    async def transcript(self, interview_id: UUID) -> list[Turn]:
        with self._lock:
            rows = self._db.execute("SELECT body FROM turns WHERE interview_id=? ORDER BY rowid", (str(interview_id),)).fetchall()
            return [Turn.model_validate_json(row["body"]) for row in rows]

    async def save_audio(self, interview_id: UUID, chunk: RecordingChunk) -> None:
        with self._lock:
            self._consented(interview_id, active=True)
            folder = self._directory(interview_id, create=True)
            name = f"{chunk.speaker}-{chunk.sequence:08d}"
            audio, metadata = folder / f"{name}.pcm", folder / f"{name}.json"
            if audio.exists() or metadata.exists() or audio.is_symlink() or metadata.is_symlink():
                raise StorageError("audio chunk already exists")
            with audio.open("xb") as file:
                file.write(chunk.audio)
            audio.chmod(0o600)
            metadata.write_text(json.dumps({"speaker": chunk.speaker, "sequence": chunk.sequence, "ts_start": chunk.ts_start, "sample_rate": chunk.sample_rate, "channels": chunk.channels}), encoding="utf-8")
            metadata.chmod(0o600)

    async def save_report(self, report: InterviewReport) -> None:
        with self._lock, self._db:
            interview = self._consented(report.interview_id)
            if interview.status not in {"completed", "aborted"} or (report.role_id, report.role_version) != (interview.role_id, interview.role_version):
                raise StorageError("finished interview and matching role required")
            candidate_ids = {turn.id for turn in await self.transcript(interview.id) if turn.speaker == "candidate"}
            if any(set(score.evidence_turn_ids) - candidate_ids for score in report.scores):
                raise StorageError("report evidence unavailable")
            self._db.execute("INSERT OR REPLACE INTO reports VALUES(?,?)", (str(report.interview_id), report.model_dump_json()))

    async def get_report(self, interview_id: UUID) -> InterviewReport | None:
        with self._lock:
            row = self._db.execute("SELECT body FROM reports WHERE interview_id=?", (str(interview_id),)).fetchone()
            return InterviewReport.model_validate_json(row["body"]) if row else None

    async def set_report_state(self, interview_id: UUID, status: str) -> None:
        if status not in {"queued", "running", "failed"}:
            raise StorageError("invalid report status")
        with self._lock, self._db:
            self._get(interview_id)
            self._db.execute("INSERT OR REPLACE INTO report_states VALUES(?,?)", (str(interview_id), status))

    async def review_list(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._db.execute("""SELECT i.body, r.body AS report_body, s.status AS report_status
                FROM interviews i LEFT JOIN reports r ON r.interview_id=i.id
                LEFT JOIN report_states s ON s.interview_id=i.id ORDER BY i.rowid DESC LIMIT ?""", (limit,)).fetchall()
            result = []
            for row in rows:
                interview = Interview.model_validate_json(row["body"])
                report = InterviewReport.model_validate_json(row["report_body"]) if row["report_body"] else None
                result.append({"id": str(interview.id), "name": interview.candidate.name,
                    "role_id": interview.role_id, "status": interview.status,
                    "created_at": interview.created_at.isoformat(),
                    "report_status": "ready" if report else (row["report_status"] or "not_generated"),
                    "report_kind": ("mock" if "mock_scoring" in report.flags else "anthropic") if report else None})
            return result

    async def recover_report_states(self):
        with self._lock, self._db:
            self._db.execute("""UPDATE report_states SET status='failed'
                WHERE status IN ('queued','running') AND interview_id NOT IN
                (SELECT interview_id FROM reports)""")

    async def save_survey(self, interview_id: UUID, clarity: int, fairness: int, comment: str) -> None:
        if not 1 <= clarity <= 5 or not 1 <= fairness <= 5 or len(comment) > 2000:
            raise StorageError("invalid survey")
        with self._lock, self._db:
            interview = self._consented(interview_id)
            if interview.status not in {"completed", "aborted"}:
                raise StorageError("finished interview required")
            self._db.execute("INSERT OR REPLACE INTO surveys VALUES(?,?)", (str(interview_id), json.dumps({"clarity": clarity, "fairness": fairness, "comment": comment})))

    async def delete(self, interview_id: UUID) -> None:
        with self._lock:
            folder = self._directory(interview_id)
            # Delete files first: if filesystem deletion fails, retain the DB row for retry.
            if folder.exists():
                shutil.rmtree(folder)
            with self._db:
                self._db.execute("DELETE FROM interviews WHERE id=?", (str(interview_id),))

    async def purge_expired(self, before: datetime) -> int:
        with self._lock:
            rows = self._db.execute("SELECT body FROM interviews").fetchall()
            expired = []
            for row in rows:
                interview = Interview.model_validate_json(row["body"])
                origin = interview.ended_at or interview.created_at
                if origin < before:
                    expired.append(interview.id)
            for interview_id in expired:
                await self.delete(interview_id)
            if expired:
                self._db.execute("VACUUM")
            return len(expired)
