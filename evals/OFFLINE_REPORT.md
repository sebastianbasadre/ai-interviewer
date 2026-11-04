# Resultados offline — 2026-11-02

Ejecutado en homelab `192.168.2.6`, WSL2 NVIDIA-Workbench, Python 3.12.16:

```bash
PYTHONPATH=src make test VENV=/home/workbench/.venvs/ai-interviewer
PYTHONPATH=src /home/workbench/.venvs/ai-interviewer/bin/python -m evals.run_evals --runs 3
```

- Suite de snapshot QA: **78 pruebas pasadas**, incluyendo motor, API/almacenamiento y diez
  pruebas de integración/evaluación.
- Harness: **33 sesiones sintéticas offline**, cero fallos estructurales registrados.
- Resultados locales: `evals/results/20261102T225240467142Z.json` y `.md`, excluidos de Git.
- El E2E usa el motor determinista real, FastAPI y SQLite; solo el proveedor de puntuación
  está simulado.
- Probado consentimiento → sala → seis competencias → cierre → informe → encuesta → eliminación.
- También probado reinicio/reanudación preservando plazo y conteos de seguimientos, y cierre
  sin nuevas solicitudes cuando expira el tiempo.

Todas las métricas de calidad del modelo permanecen **not_evaluated**. La puntuación
simulada no asignó números. Esta ejecución no establece ranking, precisión, resistencia
semántica a inyecciones, ausencia semántica de datos sensibles ni latencia real. No
autoriza un piloto con personas. La propuesta G3 y los límites están en [README.md](README.md).

Snapshot probado: motor `e86e064`, API `eaac62c` y entregables QA en esta rama.
Las correcciones posteriores del dueño y la integración requieren volver a ejecutar esta
suite. La advertencia de deprecación de HTTPX en TestClient espera la decisión del dueño
de la dependencia; no impide las pruebas.
