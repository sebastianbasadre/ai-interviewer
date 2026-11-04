"""MuseTalk local lip-sync avatar service for Pipecat 1.15.

Receives TTSAudioRawFrame chunks from the TTS stage, accumulates ~200 ms of
audio, runs MuseTalk inference on a thread pool to avoid blocking the event
loop, and pushes OutputImageRawFrame video frames downstream to the WebRTC
transport.

MuseTalk is an optional dependency.  If it is not installed the class raises
MediaUnavailable at construction time, never at import time.

Protocol note: contracts.AvatarService defines start/send_audio/interrupt/close
for a push-based integration. MuseTalkVideoService is instead a Pipecat
FrameProcessor, matching how TavusVideoService integrates with the pipeline.
Both patterns are deliberate deviations from the protocol; the protocol should
be updated to reflect the FrameProcessor-based integration in a future ADR.

Pipecat API note: OutputImageRawFrame constructor signature (image, size, format)
is assumed from the 1.15.x source. Verify against installed pipecat before first
real run: python -c "from pipecat.frames.frames import OutputImageRawFrame; help(OutputImageRawFrame)"

Design rules (from CLAUDE.md):
- Never log audio content, candidate data or model internals.
- JSON logs only; one line per structural event.
- Guard every MuseTalk import with try/except ImportError.
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# MuseTalk is NOT imported at module level.  Any import attempt lives inside the
# class constructor so that tests can mock or skip it cleanly.


class MuseTalkVideoService:
    """Pipecat 1.15 FrameProcessor that animates a portrait with MuseTalk.

    Parameters
    ----------
    model:
        A loaded MuseTalk model instance (returned by ``load_musetalk_model``
        below).  Pass the same object to every session; it is stateless between
        inference calls.
    fps:
        Target video frame rate handed to MuseTalk inference (10–30).
    chunk_ms:
        Approximate audio duration (ms) fed to each MuseTalk call.  Shorter
        values reduce latency; longer values improve lip-sync quality.
    """

    # Pipecat 1.15 frame types are imported lazily inside methods to allow this
    # module to be imported in test environments where pipecat is not installed.

    def __init__(self, model, *, fps: int = 25, chunk_ms: int = 200,
                 frame_width: int = 512, frame_height: int = 512):
        try:
            from pipecat.processors.frame_processor import FrameProcessor  # noqa: F401
        except ImportError as exc:
            from ai_interviewer.pipeline.media import MediaUnavailable
            raise MediaUnavailable(
                "Pipecat is not installed. Run: pip install -e '.[realtime]'"
            ) from exc

        if model is None:
            from ai_interviewer.pipeline.media import MediaUnavailable
            raise MediaUnavailable(
                "MuseTalk model is not loaded. Set AVATAR_MODE=musetalk and ensure "
                "MUSETALK_AVATAR_IMAGE points to a valid portrait file."
            )

        # Validate fps range matches config constraint (10–30).
        if not (10 <= fps <= 30):
            raise ValueError(f"fps must be between 10 and 30, got {fps}")

        self._model = model
        self._fps = fps
        self._chunk_ms = chunk_ms
        self._frame_size = (frame_width, frame_height)
        self._interrupted = False
        self._audio_buffer: deque[bytes] = deque()
        self._sample_rate: int = 24000  # updated on first audio frame
        self._channels: int = 1

        # Build actual FrameProcessor subclass now that pipecat is confirmed present.
        self._processor = self._build_processor()

    def _build_processor(self):
        """Return a configured FrameProcessor instance (pipecat must be installed)."""
        from pipecat.frames.frames import (
            InterruptionFrame,
            OutputImageRawFrame,
            TTSAudioRawFrame,
        )
        from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

        service = self  # capture outer self

        class _MuseTalkProcessor(FrameProcessor):
            async def process_frame(self, frame, direction: FrameDirection):
                await super().process_frame(frame, direction)

                if isinstance(frame, InterruptionFrame):
                    # Candidate began speaking — flush pending audio and stop.
                    service._interrupted = True
                    service._audio_buffer.clear()
                    await self.push_frame(frame, direction)
                    return

                if direction == FrameDirection.DOWNSTREAM and isinstance(frame, TTSAudioRawFrame):
                    service._interrupted = False
                    service._sample_rate = frame.sample_rate
                    service._channels = frame.num_channels
                    service._audio_buffer.append(frame.audio)

                    # Check whether we have accumulated enough audio for a chunk.
                    total_bytes = sum(len(b) for b in service._audio_buffer)
                    bytes_per_ms = (service._sample_rate * service._channels * 2) // 1000
                    target_bytes = bytes_per_ms * service._chunk_ms

                    if total_bytes >= target_bytes:
                        chunk = b"".join(service._audio_buffer)
                        service._audio_buffer.clear()
                        # Run inference off the event loop thread.
                        video_frames = await asyncio.to_thread(
                            service._run_inference, chunk
                        )
                        if not service._interrupted:
                            for vf in video_frames:
                                img_frame = OutputImageRawFrame(
                                    image=vf,
                                    size=service._frame_size,
                                    format="BGR",
                                )
                                await self.push_frame(img_frame, direction)

                    # Always forward the audio frame so transport can play it.
                    await self.push_frame(frame, direction)
                    return

                await self.push_frame(frame, direction)

        return _MuseTalkProcessor()

    def _run_inference(self, audio_chunk: bytes) -> list[bytes]:
        """Synchronous MuseTalk inference; called via asyncio.to_thread.

        Returns a list of raw BGR image bytes, one per video frame.
        Never logs audio content or intermediate tensors.
        """
        import struct

        try:
            import numpy as np
        except ImportError as exc:
            from ai_interviewer.pipeline.media import MediaUnavailable
            raise MediaUnavailable("numpy is required for MuseTalk inference.") from exc

        samples = (
            np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        )
        bgr_frames = self._model.inference(samples, fps=self._fps)
        result: list[bytes] = []
        for frame in bgr_frames:
            # frame is a numpy array (H, W, 3) in BGR uint8.
            if hasattr(frame, "tobytes"):
                result.append(frame.tobytes())
            else:
                result.append(bytes(frame))
        return result

    @property
    def processor(self):
        """The inner FrameProcessor to append to the Pipecat pipeline."""
        return self._processor


def load_musetalk_model(avatar_image_path: str):
    """Load a MuseTalk model from the given portrait image path.

    Returns the loaded model, or raises MediaUnavailable if MuseTalk is not
    installed.  Designed to be called via asyncio.to_thread during prepare().

    Parameters
    ----------
    avatar_image_path:
        Absolute path to the interviewer portrait (JPEG or PNG).
    """
    try:
        from musetalk import MuseTalkModel  # type: ignore[import]
    except ImportError as exc:
        from ai_interviewer.pipeline.media import MediaUnavailable
        raise MediaUnavailable(
            "MuseTalk is not installed. Run: pip install -e '.[musetalk]'"
        ) from exc

    return MuseTalkModel(avatar_image_path)
