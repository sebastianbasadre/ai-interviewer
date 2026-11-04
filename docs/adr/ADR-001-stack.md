# ADR-001: stack del piloto

Estado: aceptado por el dueño del proyecto en G1. Fecha: 2026-11-02.

## Contexto

El proyecto necesita conversación de baja latencia con interrupciones y un piloto simple,
según se especifica en CLAUDE.md.

## Decisión

Mantener Python 3.12, Pipecat 1.15.0, SmallWebRTCTransport, Silero y el analizador de
turnos, Whisper NVIDIA local (fallback OpenAI), Claude para conversación/puntuación,
OpenAI TTS (fallback Piper), Tavus y un avatar simulado por defecto. Usar FastAPI, SQLite
y archivos locales. No poner Ollama en la ruta crítica. El dueño confirmó acceso SSH al
homelab: Windows 11 con WSL2 NVIDIA-Workbench y RTX 3090. Este es el entorno WSL2
planificado, ejecutado de forma remota. La ejecución real de Whisper en CUDA aún no está
verificada.

## Consecuencias

Separar las dependencias de contrato/pruebas de las dependencias de runtime para que las
simulaciones funcionen sin GPU. Verificar las APIs de Pipecat contra el código instalado y
los ejemplos oficiales antes de usarlas. En esta etapa no se habilitan cambios implícitos
de stack ni servicios pagados.
