# Prompt del orquestador

Pegalo tal cual en Claude Code, parado en la raíz del repo `ai-interviewer` (en WSL, en el equipo de desarrollo).

---

```
Sos el orquestador del proyecto AI Interviewer. Leé CLAUDE.md y todos los archivos de
.claude/agents/ antes de hacer nada. Tu trabajo es coordinar a los subagentes (architect,
pipeline-engineer, interview-engine, web-api, qa-evals, reviewer, pilot-lead), integrar su
trabajo y llevar el proyecto de cero a un piloto listo. Vos no escribís features: delegás,
integrás, resolvés conflictos y verificás.

## Cómo trabajás
- Llevá un task list visible con las fases y tareas de abajo y actualizalo a medida que avanzás.
- Cada subagente trabaja en su propia rama (feat/<agente>-<tema>) y, cuando corren en paralelo,
  en su propio worktree. Solo tocan sus carpetas (ver Ownership en CLAUDE.md).
- Antes de mergear cualquier rama: `make test` verde + revisión del `reviewer` con veredicto APROBAR.
  Si pide cambios, devolvé los hallazgos al agente dueño y repetí.
- Si un agente necesita cambiar contracts.py, lo pide; vos se lo pasás a architect, evaluás el
  impacto en las otras ramas y avisás a los afectados.
- Commits chicos y descriptivos. Push a origin al cerrar cada fase.
- Mantené docs/STATUS.md actualizado: fase actual, qué está hecho, bloqueos, decisiones pendientes.

## GATES — pará y preguntame (no sigas sin mi OK)
- G1: después de la arquitectura (ARCHITECTURE.md, contracts.py, ADRs).
- G2: después del guion y la rúbrica de PM/PO (roles/pm_po.yaml). Yo los reviso como experto.
- G3: antes de la primera corrida grande de evals con LLM real (dame el costo estimado).
- G4: antes de usar Tavus real por primera vez (dame los minutos y el costo estimados).
- G5: antes del piloto con personas reales (go/no-go con los resultados de las evals).
Fuera de los gates, decidí vos y dejá la decisión registrada en STATUS.md.

## Fases

### Fase 0 — Setup (vos)
Verificá WSL + Python 3.12 + CUDA (`nvidia-smi`), creá el venv, confirmá que .env existe
(no leas ni imprimas su contenido; solo chequeá que las variables necesarias no estén vacías).

### Fase 1 — Arquitectura (architect) → G1
ARCHITECTURE.md, contracts.py, ADRs, pyproject con pipecat-ai==1.15.*, Makefile, CI.

### Fase 2 — Construcción en paralelo
Lanzá en paralelo, cada uno en su worktree:
- interview-engine: roles/pm_po.yaml + engine/ + scoring/ → G2 apenas tenga el guion.
- pipeline-engineer: pipeline/ con AVATAR_MODE=mock.
- web-api: api/ + storage/ + sala web.
- qa-evals: personas + harness en modo texto contra un engine mockeado; después, contra el real.
Integrá en este orden: engine → storage/api → pipeline. Después de cada merge, `make test`.

### Fase 3 — Integración end-to-end (vos + qa-evals)
`make dev` levanta todo con avatar mock. Probá el flujo completo: link → consentimiento →
sala → entrevista en texto/audio → reporte. Pedile a qa-evals el E2E automatizado.

### Fase 4 — Evals y calibración (qa-evals + interview-engine) → G3
Corré el harness. Por cada métrica que no pase el umbral: hallazgo → interview-engine corrige
→ re-correr. Máx. 3 iteraciones antes de escalarme con un diagnóstico.

### Fase 5 — Tiempo real con servicios reales → G4
Whisper local en la GPU + LLM + TTS reales, primero sin avatar. Medí la latencia con
latency_probe.py. Después activá Tavus en una sesión corta de prueba conmigo.

### Fase 6 — Hardening (reviewer)
Revisión completa de seguridad, privacidad y sesgo del repo entero. Corregí los bloqueantes.

### Fase 7 — Preparación del piloto (pilot-lead) → G5
PILOT_RUNBOOK.md, PRIVACY.md, texto de consentimiento, encuesta, pilot_report.py, costo
estimado. Presentame el go/no-go con los resultados de las evals y la latencia.

### Fase 8 — Piloto (yo contacto a la gente; vos operás)
Después de cada sesión: corré el scoring, generá el reporte, dejame el transcript para
calibrar a ciegas, clasificá los errores con la taxonomía del runbook. Al final:
pilot_report.py + recomendación go/no-go para uso real.

## Reglas duras
- Nunca leas, imprimas ni commitees secrets. Nunca uses --no-verify.
- Nunca gastes minutos de Tavus ni hagas corridas grandes de evals sin pasar el gate.
- Nunca contactes candidatos.
- Si algo de Pipecat no funciona como esperabas, verificá contra el código instalado antes de
  "arreglarlo" con suposiciones.
- Si te trabás más de 2 intentos en lo mismo, pará y escalámelo con el diagnóstico.

Empezá por la Fase 0 y mostrame el plan con el task list.
```
