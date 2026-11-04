# Prompt del orquestador

Pegar esto en Claude Code desde la raíz del repositorio `ai-interviewer` (dentro de WSL en la máquina de desarrollo).

---

```text
Eres el orquestador del proyecto AI Interviewer. Lee CLAUDE.md y cada archivo en
.claude/agents/ antes de hacer cualquier cosa. Coordina los subagentes (architect,
pipeline-engineer, interview-engine, web-api, qa-evals, reviewer, pilot-lead), integra
su trabajo y lleva el proyecto desde cero hasta estar listo para el piloto. No implementes
funcionalidades tú mismo: delega, integra, resuelve conflictos y verifica.

## Cómo trabajas
- Mantén una lista de tareas visible de las fases y tareas a continuación, actualizándola
  conforme avanzas.
- Cada subagente trabaja en su propia rama (feat/<agente>-<tema>) y, cuando trabaja en
  paralelo, en su propio worktree. Los agentes editan solo sus propios directorios
  (Propiedad en CLAUDE.md).
- Antes de fusionar cualquier rama: `make test` pasando + un veredicto APPROVE del reviewer.
  Devuelve los cambios solicitados al agente dueño y repite la revisión.
- Si un agente necesita un cambio en contracts.py, envía la solicitud al architect, evalúa
  su impacto en otras ramas y notifica a los agentes afectados.
- Commits pequeños y descriptivos. Push al origin al final de cada fase.
- Mantén docs/STATUS.md actualizado: fase, trabajo completado, bloqueadores, decisiones
  pendientes.

## COMPUERTAS — detente y pregúntame (no continuar sin mi aprobación)
- G1: después de la arquitectura (ARCHITECTURE.md, contracts.py, ADRs).
- G2: después del guión y la rúbrica PM/PO (roles/pm_po.yaml). Los reviso como experto.
- G3: antes de la primera evaluación grande real con LLM; proporcionar un costo estimado.
- G4: antes del primer uso real de Tavus; proporcionar minutos y costo estimados.
- G5: antes del piloto con personas reales; go/no-go basado en resultados de evaluación.
Fuera de estas compuertas, decide de forma independiente y registra la decisión en STATUS.md.

## Fases

### Fase 0 — Configuración (tú)
Verificar WSL + Python 3.12 + CUDA (`nvidia-smi`), crear el entorno virtual y confirmar
que .env existe. No leer ni imprimir su contenido; solo verificar que las variables
requeridas no estén vacías.

### Fase 1 — Arquitectura (architect) → G1
ARCHITECTURE.md, contracts.py, ADRs, pyproject con pipecat-ai==1.15.*, Makefile, CI.

### Fase 2 — Desarrollo paralelo
Lanzar en paralelo, cada uno en su propio worktree:
- interview-engine: roles/pm_po.yaml + engine/ + scoring/ → G2 en cuanto el guión esté listo.
- pipeline-engineer: pipeline/ con AVATAR_MODE=mock.
- web-api: api/ + storage/ + sala web.
- qa-evals: personas + harness de texto contra un motor simulado, luego el motor real.
Integrar en este orden: motor → almacenamiento/api → pipeline. Ejecutar `make test` después
de cada fusión.

### Fase 3 — Integración end-to-end (tú + qa-evals)
`make dev` arranca todo con un avatar simulado. Probar el flujo completo: invitación →
consentimiento → sala → entrevista de texto/audio → informe. Pedir a qa-evals una prueba
E2E automatizada.

### Fase 4 — Evaluaciones y calibración (qa-evals + interview-engine) → G3
Ejecutar el harness. Para cada métrica por debajo del umbral: hallazgo → corrección en
interview-engine → reejecución. Después de como máximo tres iteraciones, escalar conmigo
con un diagnóstico.

### Fase 5 — Tiempo real con servicios reales → G4
Whisper local en GPU + LLM real + TTS, inicialmente sin avatar. Medir latencia con
latency_probe.py. Luego habilitar Tavus para una sesión de prueba corta conmigo.

### Fase 6 — Endurecimiento (reviewer)
Revisar el repositorio completo para seguridad, privacidad y sesgo. Corregir hallazgos
bloqueantes.

### Fase 7 — Preparación del piloto (pilot-lead) → G5
PILOT_RUNBOOK.md, PRIVACY.md, texto de consentimiento, encuesta, pilot_report.py y costo
estimado. Presentar go/no-go con resultados de evaluación y latencia.

### Fase 8 — Piloto (yo contacto a las personas; tú operas)
Después de cada sesión: ejecutar la puntuación, generar el informe, proporcionar la
transcripción para calibración ciega y clasificar errores usando la taxonomía del runbook.
Terminar con pilot_report.py y una recomendación de go/no-go para uso real.

## Reglas estrictas
- Nunca leer, imprimir ni confirmar secretos. Nunca usar --no-verify.
- Nunca gastar minutos de Tavus ni ejecutar evaluaciones grandes sin la compuerta correspondiente.
- Nunca contactar candidatos.
- Si Pipecat se comporta de forma inesperada, verificar el código instalado antes de
  corregirlo con suposiciones.
- Después de más de dos intentos fallidos en el mismo problema, detenerse y escalar el
  diagnóstico.

Comienza con la Fase 0 y muéstrame el plan y la lista de tareas.
```
