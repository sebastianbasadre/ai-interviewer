# ADR-001: pilot stack

Status: accepted by the project owner at G1. Date: 2026-11-02.

## Context

The project needs low-latency conversation with interruptions and a simple pilot, as specified in CLAUDE.md.

## Decision

Keep Python 3.12, Pipecat 1.15.0, SmallWebRTCTransport, Silero and the turn analyzer,
local NVIDIA Whisper (OpenAI fallback), Claude for conversation/scoring, OpenAI TTS
(Piper fallback), Tavus, and a mock avatar by default. Use FastAPI, SQLite and local files.
Do not put Ollama on the critical path. The owner confirmed SSH access to the homelab:
Windows 11 with WSL2 NVIDIA-Workbench and RTX 3090. This is the planned WSL2 environment,
run remotely. Real Whisper execution on CUDA remains unverified.

## Consequences

Separate contract/test dependencies from runtime dependencies so mocks work without a GPU.
Verify Pipecat APIs against installed code and official examples before use.
No implicit stack changes or paid services are enabled at this stage.
