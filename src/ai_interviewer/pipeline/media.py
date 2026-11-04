"""Pipecat 1.15 media bridge. The API's engine remains the only phase authority.

Local Whisper/Piper process audio. Tavus is constructed only after explicit enablement,
active consent and authenticated signaling. No candidate video is
requested. Media is transient; only the existing text transcript is persisted.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable
from uuid import UUID


class MediaUnavailable(Exception):
    """Safe public diagnostic; never include provider errors or credentials."""


@dataclass
class LivePeer:
    connection: object
    task: asyncio.Task | None = None
    worker: object | None = None
    runner: object | None = None


class MediaManager:
    def __init__(self, settings):
        self.settings = settings
        self.peers: dict[UUID, LivePeer] = {}
        self._lock = asyncio.Lock()
        self._models = None
        self._voices = {}
        self._musetalk = None  # loaded in prepare() when avatar_mode="musetalk"

    async def prepare(self):
        """Download/load local models once, outside any invitation request."""
        from loguru import logger
        # Pipecat/provider debug logs can contain transcripts and URLs. Disable their
        # namespace at every level; application diagnostics use fixed messages only.
        logger.disable("pipecat")
        from pipecat.services.piper.tts import PiperTTSService
        from faster_whisper import WhisperModel
        from piper import PiperVoice
        from piper.download_voices import download_voice
        from pipecat.services.piper.tts import PIPER_CACHE_DIR

        def load():
            PIPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            for language, voice in {"es": self.settings.piper_voice, "en": self.settings.piper_english_voice}.items():
                voice_path = PIPER_CACHE_DIR / (voice + ".onnx")
                if not voice_path.exists():
                    download_voice(voice, PIPER_CACHE_DIR)
                self._voices[language] = PiperVoice.load(voice_path)
            model = WhisperModel(self.settings.whisper_model, device=self.settings.whisper_device,
                                 compute_type="int8" if self.settings.whisper_device == "cpu" else "float16")
            return model

        def load_musetalk():
            """Load MuseTalk model on the thread pool; never blocks the event loop."""
            from ai_interviewer.pipeline.musetalk_service import load_musetalk_model
            avatar_image = self.settings.musetalk_avatar_image
            if avatar_image is None:
                raise MediaUnavailable(
                    "MUSETALK_AVATAR_IMAGE is required when AVATAR_MODE=musetalk."
                )
            return load_musetalk_model(str(avatar_image))

        self._models = await asyncio.to_thread(load)
        if self.settings.avatar_mode == "musetalk" and self.settings.musetalk_enabled:
            self._musetalk = await asyncio.to_thread(load_musetalk)

    async def offer(self, interview_id: UUID, *, sdp: str, type: str,
                    submit: Callable[[str], Awaitable[dict]], initial_text: str, deadline: datetime):
        if self._models is None:
            raise MediaUnavailable("Local audio is not ready yet.")
        async with self._lock:
            if self.peers:
                raise MediaUnavailable("An audio connection is already active. Disconnect it before retrying.")
            from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
            connection = SmallWebRTCConnection(connection_timeout_secs=20)
            peer = LivePeer(connection)
            self.peers[interview_id] = peer
            try:
                await asyncio.wait_for(connection.initialize(sdp=sdp, type=type), 20)
                peer.task = asyncio.create_task(self._run(interview_id, peer, submit, initial_text, deadline))
                return connection.get_answer()
            except BaseException:
                self.peers.pop(interview_id, None)
                with suppress(Exception):
                    await connection.disconnect()
                raise MediaUnavailable("Could not negotiate the audio connection.") from None

    async def _run(self, interview_id, peer, submit, initial_text, deadline):
        import aiohttp
        import numpy as np
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.audio.vad.vad_analyzer import VADParams
        from ai_interviewer.engine.language import detect_language
        from pipecat.frames.frames import (Frame, InterruptionFrame, InputAudioRawFrame,
            TranscriptionFrame, TTSSpeakFrame, VADUserStartedSpeakingFrame)
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.worker import PipelineParams, PipelineWorker
        from pipecat.processors.audio.vad_processor import VADProcessor
        from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
        from pipecat.services.piper.tts import PiperTTSService
        from pipecat.services.stt_service import SegmentedSTTService
        from pipecat.transports.base_transport import TransportParams
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
        from pipecat.utils.time import time_now_iso8601
        from pipecat.workers.runner import WorkerRunner

        manager = self

        class LocalSTT(SegmentedSTTService):
            @property
            def wants_wav_segments(self):
                return False

            async def run_stt(self, audio):
                samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
                def transcribe():
                    segments, _ = manager._models.transcribe(samples, language=None, beam_size=1,
                                                             condition_on_previous_text=False)
                    return " ".join(s.text.strip() for s in segments if s.no_speech_prob < .6 and s.avg_logprob > -1)
                try:
                    text = await asyncio.wait_for(asyncio.to_thread(transcribe), 20)
                    if text.strip():
                        yield TranscriptionFrame(text=text, user_id=str(interview_id), timestamp=time_now_iso8601())
                except Exception:
                    peer.connection.send_app_message({"type": "media-error", "message": "Could not transcribe audio. You can type your answer."})

        class EngineBridge(FrameProcessor):
            async def process_frame(self, frame: Frame, direction: FrameDirection):
                await super().process_frame(frame, direction)
                if direction == FrameDirection.DOWNSTREAM and isinstance(frame, TranscriptionFrame):
                    try:
                        # Noise/VAD alone must not cut off the interviewer. Only a
                        # recognized answer interrupts speech already being played.
                        await self.broadcast_frame(InterruptionFrame)
                        decision = await submit(frame.text)
                        peer.connection.send_app_message({"type": "interview-turn", "candidate": frame.text, "decision": decision})
                        if decision["text"]:
                            await self.push_frame(TTSSpeakFrame(text=decision["text"]))
                        if decision["end_session"]:
                            await peer.worker.stop_when_done()
                    except Exception:
                        peer.connection.send_app_message({"type": "media-error", "message": "Could not save your answer. Reconnect or continue by text."})
                        await peer.runner.cancel()
                    return
                await self.push_frame(frame, direction)

        try:
            remaining = min(self.settings.media_max_minutes * 60,
                            (deadline - datetime.now(timezone.utc)).total_seconds())
            if self.settings.tavus_enabled:
                remaining = min(remaining, self.settings.tavus_max_minutes_per_session * 60)
            if remaining < 1:
                raise MediaUnavailable("Interview time limit reached.")
            video_enabled = self.settings.tavus_enabled or (
                self.settings.musetalk_enabled and self.settings.avatar_mode == "musetalk"
            )
            transport = SmallWebRTCTransport(peer.connection, TransportParams(
                audio_in_enabled=True, audio_out_enabled=True,
                video_out_enabled=video_enabled, video_out_is_live=True,
                video_out_width=1280, video_out_height=720,
                audio_out_auto_silence=not video_enabled))
            class BilingualPiper(PiperTTSService):
                async def run_tts(self, text, context_id):
                    self._voice = manager._voices[detect_language(text, "en")]
                    async for frame in super().run_tts(text, context_id):
                        yield frame

            tts = await asyncio.to_thread(lambda: BilingualPiper(
                settings=PiperTTSService.Settings(voice=self.settings.piper_english_voice)))
            async with aiohttp.ClientSession() as session:
                processors = [transport.input(), VADProcessor(vad_analyzer=SileroVADAnalyzer(params=VADParams(
                                  confidence=.8, start_secs=.35, stop_secs=.8))),
                              LocalSTT(), EngineBridge(), tts]
                if self.settings.tavus_enabled:
                    from ai_interviewer.pipeline.tavus_compat import create_tavus_video_service
                    processors.append(create_tavus_video_service(self.settings, session,
                                                                 max_duration_seconds=int(remaining)))
                if self.settings.musetalk_enabled and self.settings.avatar_mode == "musetalk":
                    from ai_interviewer.pipeline.musetalk_service import MuseTalkVideoService
                    musetalk_service = MuseTalkVideoService(
                        self._musetalk,
                        fps=self.settings.musetalk_fps,
                    )
                    processors.append(musetalk_service.processor)
                processors.append(transport.output())
                worker = PipelineWorker(Pipeline(processors), enable_rtvi=False,
                    params=PipelineParams(audio_in_sample_rate=16000, audio_out_sample_rate=24000),
                    idle_timeout_secs=90)
                peer.worker = worker
                runner = WorkerRunner(handle_sigint=False)
                peer.runner = runner
                await runner.add_workers(worker)

                @transport.event_handler("on_client_connected")
                async def connected(transport, client):
                    active_avatar = (
                        "tavus" if self.settings.tavus_enabled
                        else "musetalk" if (self.settings.musetalk_enabled and self.settings.avatar_mode == "musetalk")
                        else "none"
                    )
                    peer.connection.send_app_message({"type": "media-ready", "avatar": active_avatar})
                    await worker.queue_frame(TTSSpeakFrame(text=initial_text))

                @transport.event_handler("on_client_disconnected")
                async def disconnected(transport, client):
                    await runner.cancel()

                async with asyncio.timeout(max(.01, remaining)):
                    await runner.run()
        except Exception:
            peer.connection.send_app_message({"type": "media-error", "message": "The audio/video connection ended. You can reconnect or continue by text."})
        finally:
            if peer.runner:
                with suppress(Exception):
                    await peer.runner.cancel()
            with suppress(Exception):
                await peer.connection.disconnect()
            if self.peers.get(interview_id) is peer:
                self.peers.pop(interview_id, None)

    async def close(self, interview_id):
        peer = self.peers.pop(interview_id, None)
        if peer:
            if peer.runner:
                await peer.runner.cancel()
            if peer.task and peer.task is not asyncio.current_task():
                peer.task.cancel()
                await asyncio.gather(peer.task, return_exceptions=True)
            await peer.connection.disconnect()

    async def close_all(self):
        for interview_id in list(self.peers):
            await self.close(interview_id)
