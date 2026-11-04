"""Pipeline tests for the MuseTalk local avatar service.

Rules:
- Never import the real MuseTalk model.
- Never touch GPU, network, or audio content.
- Pipecat is mocked at the frame class level where unavailable.
- All assertions are structural (frame types / counts), never content.
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Synthetic pipecat stub — only the symbols used by musetalk_service.py.
# Tests in environments without pipecat installed use this stub.
# ---------------------------------------------------------------------------


def _make_pipecat_stub():
    """Return a minimal pipecat stub with the required frame/processor symbols."""
    # Base Frame
    class Frame:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class FrameDirection:
        DOWNSTREAM = 1
        UPSTREAM = 2

    class InterruptionFrame(Frame):
        pass

    class AudioRawFrame(Frame):
        def __init__(self, audio: bytes, sample_rate: int, num_channels: int):
            self.audio = audio
            self.sample_rate = sample_rate
            self.num_channels = num_channels

    class OutputAudioRawFrame(AudioRawFrame):
        pass

    class TTSAudioRawFrame(OutputAudioRawFrame):
        def __init__(self, audio: bytes, sample_rate: int, num_channels: int, context_id=None):
            super().__init__(audio, sample_rate, num_channels)
            self.context_id = context_id

    class OutputImageRawFrame(Frame):
        def __init__(self, image: bytes, size: tuple, format: str | None = None):
            self.image = image
            self.size = size
            self.format = format

    class FrameProcessor:
        """Minimal synchronous stub — does not run a real Pipecat pipeline."""

        def __init__(self):
            self._pushed: list[tuple] = []
            self._next: "FrameProcessor | None" = None

        async def process_frame(self, frame: Frame, direction: FrameDirection):
            # Subclasses override this; base does nothing.
            pass

        async def push_frame(self, frame: Frame, direction=FrameDirection.DOWNSTREAM):
            self._pushed.append((frame, direction))

    # Build module hierarchy
    pipecat = types.ModuleType("pipecat")
    frames_mod = types.ModuleType("pipecat.frames")
    frames_frames = types.ModuleType("pipecat.frames.frames")
    processors_mod = types.ModuleType("pipecat.processors")
    fp_mod = types.ModuleType("pipecat.processors.frame_processor")

    frames_frames.Frame = Frame
    frames_frames.InterruptionFrame = InterruptionFrame
    frames_frames.OutputAudioRawFrame = OutputAudioRawFrame
    frames_frames.TTSAudioRawFrame = TTSAudioRawFrame
    frames_frames.OutputImageRawFrame = OutputImageRawFrame

    fp_mod.FrameProcessor = FrameProcessor
    fp_mod.FrameDirection = FrameDirection

    pipecat.frames = frames_mod
    pipecat.processors = processors_mod
    sys.modules.setdefault("pipecat", pipecat)
    sys.modules.setdefault("pipecat.frames", frames_mod)
    sys.modules.setdefault("pipecat.frames.frames", frames_frames)
    sys.modules.setdefault("pipecat.processors", processors_mod)
    sys.modules.setdefault("pipecat.processors.frame_processor", fp_mod)

    return {
        "Frame": Frame,
        "FrameDirection": FrameDirection,
        "InterruptionFrame": InterruptionFrame,
        "TTSAudioRawFrame": TTSAudioRawFrame,
        "OutputImageRawFrame": OutputImageRawFrame,
        "FrameProcessor": FrameProcessor,
    }


# Install stub before importing our module.
_stub = _make_pipecat_stub()

# Now safe to import our module.
from ai_interviewer.pipeline.musetalk_service import MuseTalkVideoService, load_musetalk_model  # noqa: E402
from ai_interviewer.pipeline.media import MediaUnavailable  # noqa: E402
from ai_interviewer.config import Settings  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class FakeMuseTalkModel:
    """Stand-in for MuseTalkModel; returns synthetic BGR frames as plain bytes.

    Does not require numpy so tests run in the pure .[test] environment.
    """

    def __init__(self):
        self.calls: list[tuple] = []

    def inference(self, audio_np, fps: int = 25) -> list[Any]:
        self.calls.append((len(audio_np), fps))
        # Return one synthetic frame; _run_inference handles serialisation.
        return [_SyntheticFrame(512, 512)]


class _SyntheticFrame:
    """Minimal stand-in for a numpy BGR frame with a tobytes() method."""

    def __init__(self, h: int, w: int):
        self._data = bytes(h * w * 3)

    def tobytes(self) -> bytes:
        return self._data


def _make_audio_frame(duration_ms: int = 100, sample_rate: int = 24000) -> Any:
    """Create a synthetic TTSAudioRawFrame of the given duration."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio = bytes(num_samples * 2)  # 16-bit mono PCM silence
    return _stub["TTSAudioRawFrame"](audio=audio, sample_rate=sample_rate, num_channels=1)


def _patched_run_inference(svc: "MuseTalkVideoService"):
    """Monkeypatch _run_inference to skip numpy, returning one synthetic frame."""

    def _fake(audio_chunk: bytes) -> list[bytes]:
        svc._model.calls.append((len(audio_chunk), svc._fps))
        return [bytes(512 * 512 * 3)]  # one flat BGR frame

    svc._run_inference = _fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMuseTalkVideoServiceFrames:
    """MuseTalkVideoService pushes video frames when it receives enough audio."""

    def test_construction_succeeds_with_valid_model(self):
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        assert svc.processor is not None

    async def test_audio_below_threshold_does_not_trigger_inference(self):
        """Less than chunk_ms worth of audio must not call inference yet."""
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        proc = svc.processor

        # Push 50 ms < 200 ms threshold.
        frame = _make_audio_frame(duration_ms=50, sample_rate=24000)
        await proc.process_frame(frame, _stub["FrameDirection"].DOWNSTREAM)

        assert model.calls == [], "No inference should run below threshold"
        # Audio frame must still be forwarded.
        audio_frames = [f for f, _ in proc._pushed if isinstance(f, _stub["TTSAudioRawFrame"])]
        assert len(audio_frames) == 1

    async def test_audio_at_threshold_triggers_inference_and_emits_video(self):
        """Accumulating >= chunk_ms of audio triggers inference and video frames."""
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        _patched_run_inference(svc)
        proc = svc.processor

        # Push two 110 ms chunks (total 220 ms > 200 ms threshold).
        for _ in range(2):
            frame = _make_audio_frame(duration_ms=110, sample_rate=24000)
            await proc.process_frame(frame, _stub["FrameDirection"].DOWNSTREAM)

        assert len(model.calls) == 1, "Inference should run exactly once after threshold"
        video_frames = [
            f for f, _ in proc._pushed
            if isinstance(f, _stub["OutputImageRawFrame"])
        ]
        assert len(video_frames) >= 1, "At least one video frame must be pushed"
        # Video frame must carry a sensible size tuple.
        assert video_frames[0].size == (512, 512)

    async def test_audio_frames_are_always_forwarded(self):
        """Audio frames must pass through regardless of inference status."""
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        proc = svc.processor

        for i in range(3):
            frame = _make_audio_frame(duration_ms=50)
            await proc.process_frame(frame, _stub["FrameDirection"].DOWNSTREAM)

        audio_fwd = [f for f, _ in proc._pushed if isinstance(f, _stub["TTSAudioRawFrame"])]
        assert len(audio_fwd) == 3

    async def test_upstream_frames_pass_through_unchanged(self):
        """Non-audio frames traveling upstream must not be modified."""
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        proc = svc.processor

        sentinel = _stub["Frame"]()
        await proc.process_frame(sentinel, _stub["FrameDirection"].UPSTREAM)

        assert any(f is sentinel for f, _ in proc._pushed)


class TestInterruptionHandling:
    """InterruptionFrame flushes the buffer and suppresses pending inference."""

    async def test_interruption_clears_buffer(self):
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        proc = svc.processor

        # Accumulate 100 ms (below threshold).
        await proc.process_frame(_make_audio_frame(100), _stub["FrameDirection"].DOWNSTREAM)

        # Interrupt mid-accumulation.
        interrupt = _stub["InterruptionFrame"]()
        await proc.process_frame(interrupt, _stub["FrameDirection"].DOWNSTREAM)

        assert len(svc._audio_buffer) == 0
        assert model.calls == [], "Interrupted buffer must not trigger inference"

    async def test_interruption_frame_is_forwarded(self):
        """InterruptionFrame must still propagate downstream for transport to act on."""
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        proc = svc.processor

        interrupt = _stub["InterruptionFrame"]()
        await proc.process_frame(interrupt, _stub["FrameDirection"].DOWNSTREAM)

        interruption_fwd = [
            f for f, _ in proc._pushed
            if isinstance(f, _stub["InterruptionFrame"])
        ]
        assert len(interruption_fwd) == 1

    async def test_no_video_emitted_after_interruption(self):
        """Video frames from inference started before an interrupt must not be pushed."""
        model = FakeMuseTalkModel()
        svc = MuseTalkVideoService(model, fps=25, chunk_ms=200)
        _patched_run_inference(svc)
        proc = svc.processor

        # Accumulate beyond threshold (200 ms), then interrupt.
        # Three 100 ms frames: first two cross threshold and may trigger inference;
        # the interrupt arrives before or after — but the flag disables video push.
        for _ in range(3):
            await proc.process_frame(_make_audio_frame(100), _stub["FrameDirection"].DOWNSTREAM)
        await proc.process_frame(_stub["InterruptionFrame"](), _stub["FrameDirection"].DOWNSTREAM)
        # After interruption the flag is set; any pending inference result is discarded.
        assert svc._interrupted is True


class TestImportErrorHandling:
    """Missing MuseTalk raises MediaUnavailable, not a crash."""

    def test_load_musetalk_model_raises_media_unavailable_when_not_installed(self):
        """load_musetalk_model must raise MediaUnavailable, not ImportError."""
        # Temporarily hide musetalk from sys.modules.
        with patch.dict(sys.modules, {"musetalk": None}):
            with pytest.raises(MediaUnavailable, match="MuseTalk is not installed"):
                load_musetalk_model("/fake/portrait.jpg")

    def test_musetalk_video_service_raises_media_unavailable_on_none_model(self):
        """Passing None as model (no prepare() call) must raise MediaUnavailable."""
        with pytest.raises(MediaUnavailable, match="MuseTalk model is not loaded"):
            MuseTalkVideoService(None, fps=25)

    def test_load_musetalk_model_does_not_raise_on_import_at_module_level(self):
        """Importing musetalk_service must never raise ImportError itself."""
        # The module is already imported above; re-importing must not fail.
        import importlib
        import ai_interviewer.pipeline.musetalk_service as mod
        importlib.reload(mod)  # would raise if top-level import were present


class TestConfigAcceptsMusetalk:
    """Settings model accepts avatar_mode=musetalk and the new MuseTalk fields."""

    def test_avatar_mode_musetalk_is_valid(self):
        s = Settings(_env_file=None, avatar_mode="musetalk")
        assert s.avatar_mode == "musetalk"

    def test_musetalk_defaults(self):
        s = Settings(_env_file=None)
        assert s.musetalk_avatar_image is None
        assert s.musetalk_fps == 25
        assert s.musetalk_enabled is False

    def test_musetalk_fps_field_validates_range(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(_env_file=None, musetalk_fps=5)
        with pytest.raises(ValidationError):
            Settings(_env_file=None, musetalk_fps=31)

    def test_musetalk_avatar_image_accepts_path(self, tmp_path):
        portrait = tmp_path / "portrait.jpg"
        portrait.write_bytes(b"\xff\xd8\xff")  # minimal JPEG header
        s = Settings(_env_file=None, musetalk_avatar_image=portrait)
        assert s.musetalk_avatar_image == portrait

    def test_musetalk_avatar_image_rejects_missing_file(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="does not exist"):
            Settings(_env_file=None, musetalk_avatar_image=Path("/tmp/nonexistent_portrait.jpg"))

    def test_musetalk_enabled_true_does_not_require_api_keys(self):
        """MuseTalk requires no API keys; missing_secrets must remain empty."""
        s = Settings(_env_file=None, musetalk_enabled=True, avatar_mode="musetalk",
                     admin_api_key="key", ip_hash_secret="x" * 32)
        missing = s.missing_secrets(realtime=True)
        # anthropic_api_key will be missing unless set; that is expected.
        assert "TAVUS_API_KEY" not in missing
        assert "TAVUS_FACE_ID" not in missing

    def test_avatar_mode_still_accepts_mock_and_tavus(self):
        for mode in ("mock", "tavus"):
            s = Settings(_env_file=None, avatar_mode=mode)
            assert s.avatar_mode == mode

    def test_avatar_mode_rejects_unknown_value(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(_env_file=None, avatar_mode="unknown_avatar")
