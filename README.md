# AI Interviewer — kit de arranque para Claude Code

Este kit contiene todo lo necesario para que Claude Code (CLI) orqueste el proyecto con un equipo de subagentes.

## Contenido

```
CLAUDE.md                     — contexto, stack, reglas y diseño de la entrevista
.env.example                  — variables necesarias (copiar a .env)
.claude/agents/
  architect.md                — arquitectura, contratos, ADRs
  pipeline-engineer.md        — Pipecat: WebRTC, VAD, STT, TTS, Tavus
  interview-engine.md         — guion PM/PO, máquina de estados, scoring, reporte
  web-api.md                  — FastAPI, links, consentimiento, sala, storage
  qa-evals.md                 — candidatos sintéticos, métricas, E2E, latencia
  reviewer.md                 — revisión independiente de código, seguridad y privacidad
  pilot-lead.md               — runbook, calibración, go/no-go, privacidad
docs/ORCHESTRATOR_PROMPT.md   — el prompt que pegás en Claude Code
```

## Pasos (en el equipo de desarrollo, dentro de WSL2)

```bash
# 1. Crear el repo y clonarlo
git clone https://github.com/sebastianbasadre/ai-interviewer.git
cd ai-interviewer

# 2. Copiar el kit adentro (ajustá la ruta a donde lo descomprimiste)
cp -r /mnt/c/Users/<vos>/Downloads/ai-interviewer-kit/. .

# 3. Secrets
cp .env.example .env
nano .env        # ANTHROPIC_API_KEY, OPENAI_API_KEY, TAVUS_API_KEY, TAVUS_REPLICA_ID

# 4. Python 3.12 (si no lo tenés en WSL)
sudo apt install -y python3.12 python3.12-venv

# 5. Primer commit
git add . && git commit -m "chore: kit de arranque del orquestador" && git push -u origin main

# 6. Arrancar Claude Code y pegar el prompt de docs/ORCHESTRATOR_PROMPT.md
claude
```

## Tips

- Verificá que `.env` esté en `.gitignore` antes del primer push (el architect lo agrega; si commiteás antes, agregalo vos).
- La réplica de Tavus (`TAVUS_REPLICA_ID`): usá una de stock para empezar. Si después querés una réplica con tu cara y voz, hacelo con tu consentimiento y dejando claro en la sala que es un avatar de IA.
- Si querés que CodeRabbit revise los PRs, instalalo en el repo: complementa al `reviewer`.
- Los gates G1–G5 son los momentos en que el orquestador para y te pide OK. G2 (guion y rúbrica de PM/PO) es donde más valor agrega tu criterio.
