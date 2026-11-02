# ADR-001: stack del piloto

Estado: propuesto para G1. Fecha: 2026-11-02.

## Contexto
Se necesita conversación de baja latencia con interrupciones y un piloto simple, según CLAUDE.md.

## Decisión
Mantener Python 3.12, Pipecat 1.15.0, SmallWebRTCTransport, Silero y turn analyzer,
Whisper local NVIDIA (OpenAI fallback), Claude para conversación/scoring, OpenAI TTS
(Piper fallback), Tavus y avatar mock por defecto. FastAPI, SQLite y archivos locales.
No usar Ollama en el camino crítico. El responsable confirmó homelab por SSH: Windows 11
con WSL2 NVIDIA-Workbench y RTX 3090. Es el mismo entorno WSL2 previsto, ejecutado remotamente.
La ejecución real de Whisper en CUDA queda por verificar.

## Consecuencias
Se separan dependencias de contratos/tests de runtime para permitir mocks sin GPU.
Las APIs de Pipecat se verifican en código instalado y ejemplos oficiales antes de usarlas.
No hay cambios de stack implícitos ni servicios pagos activados en esta fase.
