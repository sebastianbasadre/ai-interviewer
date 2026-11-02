# Resultado offline — 2026-11-02

Se ejecutó en el homelab `192.168.2.6`, WSL2 NVIDIA-Workbench, Python 3.12.16:

```bash
PYTHONPATH=src make test VENV=/home/workbench/.venvs/ai-interviewer
PYTHONPATH=src /home/workbench/.venvs/ai-interviewer/bin/python -m evals.run_evals --runs 3
```

- Suite del snapshot QA: **78 tests pasan** (incluye motor, API/storage y diez tests de integración/evals).
- Harness: **33 sesiones sintéticas offline**, cero fallas estructurales registradas.
- Resultados locales: `evals/results/20261102T225240467142Z.json` y `.md`, excluidos de Git.
- El E2E usa motor determinístico, FastAPI y SQLite reales; únicamente el proveedor de scoring es mock.
- Se probó consentimiento → sala → seis competencias → cierre → reporte → encuesta → borrado.
- También se probó reinicio/reanudación conservando deadline y repreguntas, y cierre sin nuevas solicitudes al vencer el tiempo.

Todas las métricas de calidad de modelos permanecen **not_evaluated**. El scoring mock no
asignó números. Esta corrida no acredita ranking, precisión, resistencia semántica a
inyección, ausencia semántica de datos sensibles ni latencia real. No habilita un piloto
con personas. La propuesta G3 y sus límites están en [README.md](README.md).

Snapshot probado: engine `e86e064` y API `eaac62c`, más entregables QA de esta rama.
Las correcciones posteriores de los dueños y su integración requieren volver a correr
esta suite. La advertencia de deprecación del TestClient HTTPX está pendiente de decisión
del responsable de dependencias; no impide las pruebas.
