# AI Interviewer

Structured PM/PO interviews with human review. The current runtime provides a
**demo workflow**: consent, session, transcript and report. It can enable real local
Whisper/Piper audio and an optional Tavus avatar, verified in a synthetic session
with 1280x720 video. Mock scoring leaves scores `null`; optional Claude scoring produces
scores with evidence for human review and requires pilot validation.
Audio/avatar setup and limits: [docs/MEDIA_SETUP.md](docs/MEDIA_SETUP.md).
Optional Claude answer analysis: [docs/CONVERSATION_SETUP.md](docs/CONVERSATION_SETUP.md).
Real reports and the reviewer interface: [docs/REPORTS.md](docs/REPORTS.md).

## Run in the homelab

Verified environment: Windows 11, WSL2 NVIDIA-Workbench, Python 3.12 and RTX 3090.
Run the following commands inside WSL2 from the checkout root. The launcher listens
only on `127.0.0.1:8000`, with one worker and no access logs, to protect invitation tokens.

```bash
make install-test
cp .env.example .env  # first run only; do not overwrite existing configuration
```

Set independent `ADMIN_API_KEY` and `IP_HASH_SECRET` values in `.env`, each containing
at least 32 random characters. Set `PRIVACY_CONTACT` to the actual person responsible
for deletion requests. Generate secrets with a secret manager; do not paste them into
commits, logs or chats. Keep `APP_MODE=mock`, `AVATAR_MODE=mock` and
`PUBLIC_BASE_URL=http://localhost:8000`. This workflow needs no Anthropic, OpenAI or
Tavus keys. Startup rejects missing or short secrets. Errors show field names, never values.

```bash
make test
make dev
```

For a virtual environment at another path, use `make VENV=/path/to/venv test` and the
same parameter for `dev`. The homelab environment is at
`/home/workbench/.venvs/ai-interviewer`. Use an SSH tunnel to the local port when opening
the application from another machine; do not expose this launcher directly to the LAN.
The public URL must match the browser's origin. Outside localhost, the API requires HTTPS.

For an authorized mock demo over HTTP on a private LAN, enable `ALLOW_MOCK_LAN_HTTP=true`
and set `PUBLIC_BASE_URL=http://192.168.2.6:8000`. This exception accepts only RFC1918
private IPs with both app and avatar in mock mode; other origins still require HTTPS.
The launcher still listens on loopback: configure host port forwarding and a firewall
rule restricted to the local subnet.

## Synthetic walkthrough

1. Open `/` and confirm `mode: mock`. Create an invitation with
   `POST /admin/interviews`, header `X-Admin-Key`, and JSON
   `{"role_id":"pm_po","name":"Synthetic","email":"synthetic@example.invalid"}`.
   Set the header in a private HTTP client; keep the secret out of command history.
2. Open the returned `link`, accept consent and enter the text room.
3. Complete or end the session. Generate the report using
   `POST /admin/interviews/{id}/report` with the same admin header.
4. Read it with `GET` on that path. It should contain `mock_scoring` and six `null`
   scores. Delete test data using `DELETE /admin/interviews/{id}`.

The link is a credential: do not share or log it. Admin endpoints require authentication
even in mock mode. Interviews cannot start without consent. SQLite and files are stored
in `DATA_DIR`, with configurable retention (30 days by default).

## Evaluations and audio/video

```bash
make eval        # offline harness; no providers or token costs
make install     # also installs Pipecat 1.15.0 for optional frame tests
```

The offline harness checks structure and safety using test doubles. Unevaluated semantic
metrics are not presented as passing. Large real LLM evaluations require G3 and a cost
estimate. `APP_MODE=real` and `make dev-tavus` remain blocked pending provider integration
and the relevant gates. Tavus requires G4 before consuming minutes.

The room supports optional WebRTC with local STT/TTS. Chrome audio over the LAN was
verified, including synthetic transcription and spoken responses. Audiovisual recording,
p50/p95 latency, measured synchronization and semantic quality remain pending. Do not
claim pilot readiness until evaluations, privacy review and G5 are complete; do not use
with real candidates yet.

Architecture and decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Status and gates: [docs/STATUS.md](docs/STATUS.md). Agent rules: [CLAUDE.md](CLAUDE.md).
