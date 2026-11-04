# Project status

This file records chronological checkpoints. Later entries supersede earlier pending
items; historical test counts refer to separate snapshots and are not cumulative.

## Initial phase

Phase 0 prepared except credentials; G1 and G2 approved by the owner; Phase 2 in development.

## Tasks at the initial checkpoint

- [x] Read CLAUDE.md, README, orchestrator prompt and seven agent guides.
- [x] Verify SSH access to sbasadre@192.168.2.6 with the existing identity.
- [x] Verify Windows 11 + WSL2 NVIDIA-Workbench and RTX 3090 (24 GB).
- [x] Install Python 3.12.16 in WSL user space using uv 0.13.6.
- [x] Create /home/workbench/.venvs/ai-interviewer on the homelab.
- [ ] Complete .env credentials: template created and gitignored; no secrets read or printed at this checkpoint.
- [x] Architecture, contracts, ADRs, configuration, Makefile and CI (architect).
- [x] Homelab make test: 15 passed (Python 3.12.16).
- [x] Independent review: APPROVE; engine events and snapshot restore corrected.
- [x] G1 approved by the owner (OK).
- [x] G2 PM/PO script/rubric approved by the owner (YES), with APPROVE technical review and 19 passing tests.
- [ ] API/storage and mock pipeline on isolated branches; integrate only after passing tests and APPROVE.

## Initial decisions

- The owner specified execution on homelab 192.168.2.6 over SSH, not the local PC.
- Keep the stack and Python 3.12; run Linux through homelab WSL2.
- Mock avatar; no paid services, real evaluations or candidate contact at this checkpoint.
- Git needs a safe.directory exception for SMB ownership; apply per command, not globally.
- Architecture integrated by fast-forward after tests, APPROVE and G1. Phase 2 branches:
  feat/interview-engine-role, feat/web-api-pilot and feat/pipeline-mock.

## Initial pending work

G3 paid evaluations; G4 Tavus; G5 real pilot. GPU visible in WSL; actual Whisper/CUDA
compatibility unverified. Keep proposed 30-day retention. Persisted video scope pending;
do not implement it yet. Phase 2 web/API and pipeline checkpoints used isolated worktrees,
not yet integrated or declared complete; resumed after G2 approval.

## Development after G2

- Engine/scoring: offline implementation ready; STAR fixes and privacy test in e86e064
  (53 homelab tests), awaiting re-review.
- API/storage: eaac62c (34 tests); start/watchdog race and finish-recovery fixes in progress.
- Pipeline: 7d27646 (36 tests with Pipecat); speech/concurrency control fixed. Interruptions
  during generation stop safely until transactional factory/restore integration.
- Factory/restore contract: architect's fb44d52, awaiting integration/review.
- QA: offline harness/E2E in development; 78 tests in the combined working snapshot, no real calls.
- Runtime: local composition with mocks and development commands in progress.

Counts refer to different snapshots and must not be added. No implementation branch is
integrated without re-review and tests.

## Verified integration

- Engine e86e064 and API 12b30e6: APPROVE re-review, integrated in order.
- QA 36b0508: offline tools APPROVED; integrated by cherry-pick 36f6b11.
- Combined homelab main: 82 passing tests; 33 synthetic offline sessions, zero structural failures.
- Runtime 6451d2a: APPROVED; runtime.py, __main__.py, replace_progress implemented,
  hardened BEGIN IMMEDIATE transactions, batch VACUUM. Integrated into main.
- Real semantic quality, ranking and latency remain unevaluated.
- Before G3: integrate feat/pipeline-mock (requires re-review with main's factory/restore
  contract), then prepare a real adapter with budget reservation and an audited eval factory.

## Local audio demo — 2026-11-03

- This folder's checkout deployed separately at
  `/home/workbench/projects/ai-interviewer-folder-review`; changes unmerged/uncommitted.
- Text API, mock follow-up limited to one per competency and LAN access verified.
- HTTPS at `https://192.168.2.6:8443`, development certificate with IP SAN.
- Pipecat 1.15.0, Silero, Whisper small CPU and Piper es_AR-daniela-high connected to the room.
- Authenticated TCP Coturn enables Chrome LAN WebRTC through WSL NAT.
- Real browser smoke: secure context, connected peer, 819 received audio packets,
  synthetic speech transcribed, engine advanced to warmup. No candidate voices used.
- 96 passing offline tests before final documentation/launcher adjustments.
- No retained audio/video files: transcript stored with specific consent.
- TavusVideoService prepared as an optional stage; keys/replica missing, no usage.
- G4 pending: supply keys, confirm minutes/cost, test video/synchronization/closure.
- Evaluation model still mock; G3, quantitative latency and G5 not approved.
- Operations, restart and limitations: MEDIA_SETUP.md.

## Tavus Face/PAL migration — 2026-11-03

- Configuration: TAVUS_API_KEY, TAVUS_FACE_ID, TAVUS_PAL_ID (Echo PAL).
- TAVUS_REPLICA_ID retained as legacy configuration fallback.
- Pipecat 1.15 HTTP-session adapter: create with face_id/pal_id, query names through
  /pals, close through /conversations/{id}/end; installed SDK unchanged.
- Maximum duration also sent to Tavus; recording explicitly disabled.
- HTTP doubles and real SDK client/constructor validation; no paid calls.
- Final validation: 114 passing Pipecat-venv tests; 112 passed and two skipped (optional
  SDK) in the text venv. Deployed runtime with healthy health/media_ready.
- Live video/account resource compatibility still awaiting G4 at this checkpoint.
- Owner confirmed our engine with Tavus only as avatar: Pipecat, Whisper/Piper and Echo
  PAL. Do not replace this with the Tavus full-pipeline embed.
- Tavus credential configured; Echo PAL created with Anna Face rc9cff32ceba and verified
  from the homelab. IDs and secret stored in local/runtime .env files.
- No Tavus conversation started yet; video remained disabled pending G4.

## First real Tavus test — 2026-11-03

- Owner approved G4 for a test up to one minute. Media/Tavus limits set to one minute,
  sent to the provider as max_call_duration=60.
- Real Anna Echo PAL conversation tested in Chrome over LAN HTTPS.
- Received 1280x720 video (185 decoded frames), audio (417 received packets), synthetic
  transcription and engine advancement to warmup. No real candidates.
- End button closed the interview; Tavus API confirmed ended. Local synthetic interview
  data deleted. Exact monetary usage awaits the Tavus account.
- Runtime avatar enabled with one minute per connection; new connections consume account
  minutes. This does not approve a pilot or real candidate evaluation.
- No formal p50/p95 latency or audiovisual synchronization measurement; G5 not claimed.

## Claude analyzer integration — 2026-11-03

- Optional Anthropic Messages adapter with JSON output and strict classification.
- Follow-ups target missing situation/action/outcome; context bounded to the competency
  and retained after reconnecting. Engine retains transitions.
- Versioned consent identifies Anthropic and blocks old consent before provider submission.
- Persistent global default of 30 attempts; 512 output tokens, timeout, content-free
  errors and no automatic retries.
- 132 passing homelab tests with HTTP doubles. Scoring still mock.
- ANTHROPIC_API_KEY missing from local/runtime .env when implemented; CONVERSATION_ENABLED
  disabled. No real calls or Anthropic cost.
- Activation/test awaiting credentials; see CONVERSATION_SETUP.md.

## Anthropic credential verified — 2026-11-04

- ANTHROPIC_API_KEY present locally; authentication/model access confirmed through
  GET /v1/models/claude-haiku-5-5, without inference.
- Homelab 192.168.2.6 unreachable over SSH/22 and HTTP(S)/8000/8443 from this session.
- Could not synchronize the key or activate the remote runtime. Recover connectivity
  and run the synthetic-answer smoke test.

## Claude enabled and tested — 2026-11-04

- Homelab reachable again. Key synchronized over SSH and CONVERSATION_ENABLED=true in
  runtime configuration; healthy runtime and media prepared.
- Real API smoke with updated consent: example without outcome triggered a STAR follow-up
  (3.620 s); an outcome clarification completed the example and advanced to the next
  competency (1.409 s), without analysis_fallback. These are classification times,
  not audiovisual p50/p95 latency measurements.
- Two Anthropic attempts reserved from the persistent 30-attempt limit. Synthetic data deleted.
- No Tavus conversation during this test. Media remains limited to one minute per connection.
  New invitation prepared with Anthropic consent.
- Scoring still mock; no large evaluations or approved real pilot.
- Windows retained portproxy rules without LAN listeners after interruption; restarting
  IP Helper (iphlpsvc) restored 8000, 8443 and 3479 at 192.168.2.6. HTTPS, new consent
  and TCP TURN verified from another LAN machine.

## Opus report and human review — 2026-11-04

- Optional real Claude Opus 5.5 scoring with three runs; retains rubric/candidate-citation
  validation, median/spread, and null if any run lacks evidence.
- Persistent global three-attempt reservation per report; configured limit 12.
- Automatic background generation when sessions with updated consent end. Failures and
  cancellations neither invalidate closure nor publish partial reports.
- Private /admin/review; ADMIN_API_KEY only in memory. Data/HTML downloads require auth.
  Includes filtered citations, rubric anchors and human-review-pending status.
- Real synthetic-fixture test: Metrics null; other five numeric scores cite existing
  evidence. Three evaluations completed in 33.2 seconds. No Tavus.
- Fixed HTTP 400 schema rejection (nullable enum) with anyOf and local range validation.
  Conservative reservations consumed: three initial, one diagnostic, three for the valid
  report. No invalid report published.
- Not a complete semantic evaluation or G5 approval; operations in REPORTS.md.
- Final checkpoint validation: 140 passing tests; Chrome displayed six competencies,
  seven citations, six expandable rubrics and the insufficient-evidence case. HTML
  download/logout verified without JavaScript errors. Synthetic example retained for review.

## Conversation, interface and documentation updates — 2026-11-04

- English interface; automatic English/Spanish conversation with local Whisper detection,
  fixed translated questions and language restoration. Language preferences do not advance phases.
- Increased VAD pause tolerance; only recognized transcriptions interrupt speech.
  Browser tolerates transient disconnects; local WebRTC audio and both languages verified.
- Redesigned consent/room for desktop/mobile, video-first layout, device checks, mute,
  text fallback and completed-state feedback; browser interactions verified.
- English voice is configurable Jenny (Dioco), credited in the room; Spanish retains
  Daniela. Local synthesis verified, no additional paid voice service.
- Name requests acknowledged without repeating questions, advancing phases or spending
  follow-ups. Preferences/pending questions survive restore; name-only turns excluded
  from analysis/scoring. Latest full suite: 172 passing tests.
- Project Markdown documentation translated into English. Historical records retained.
- Tavus remains limited to one minute per connection; extension awaits explicit approval.
