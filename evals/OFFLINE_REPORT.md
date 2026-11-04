# Offline results — 2026-11-02

Executed on homelab `192.168.2.6`, WSL2 NVIDIA-Workbench, Python 3.12.16:

```bash
PYTHONPATH=src make test VENV=/home/workbench/.venvs/ai-interviewer
PYTHONPATH=src /home/workbench/.venvs/ai-interviewer/bin/python -m evals.run_evals --runs 3
```

- QA snapshot suite: **78 tests passed**, including engine, API/storage and ten integration/evaluation tests.
- Harness: **33 synthetic offline sessions**, zero recorded structural failures.
- Local results: `evals/results/20261102T225240467142Z.json` and `.md`, excluded from Git.
- E2E uses the real deterministic engine, FastAPI and SQLite; only the scoring provider is mocked.
- Tested consent → room → six competencies → closure → report → survey → deletion.
- Also tested restart/resume preserving deadline and follow-up counts, and closure without new requests when time expires.

All model-quality metrics remain **not_evaluated**. Mock scoring assigned no numbers.
This run does not establish ranking, accuracy, semantic injection resistance, semantic
absence of sensitive data or real latency. It does not authorize a pilot with people.
The G3 proposal and limits are in [README.md](README.md).

Tested snapshot: engine `e86e064`, API `eaac62c`, and QA deliverables on this branch.
Later owner fixes and integration require rerunning this suite. The TestClient HTTPX
deprecation warning awaits the dependency owner's decision; it does not prevent testing.
