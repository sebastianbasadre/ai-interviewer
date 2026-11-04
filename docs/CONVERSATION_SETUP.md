# Claude answer analysis

## Scope

`CONVERSATION_ENABLED=true` connects the engine's analyzer to Claude Haiku 5.5. Claude
classifies relevance, concrete examples, requests to repeat/end, and injection attempts;
it identifies missing situation, personal action or outcome. The engine selects the
corresponding follow-up from fixed wording and retains control of phases, six competencies,
two follow-ups per competency and timing. Tavus continues rendering Piper speech in Echo mode.

Analyze clarifications together with previous answers for that competency. A short outcome
can complete the original example, including after reconnecting. Context retains up to
three filtered contributions within a total text limit and resets for the next competency.
It excludes candidate profiles and other interviews. The conservative lexical filter does
not guarantee anonymization of free text.

Configure scoring separately: `SCORING_ENABLED=false` uses mock scores (`null` for every
competency). Optional Opus evaluation and human review are described in REPORTS.md.
The analyzer does not establish semantic calibration or G5 readiness. `APP_MODE=real`
remains blocked; enable providers explicitly within the demo.

## Configuration

Inside WSL2, install the HTTP extra alongside the deployment's existing extras:

```bash
python -m pip install -e '.[test,media,llm]'
```

Configure `.env` without printing values:

```dotenv
APP_MODE=mock
ANTHROPIC_API_KEY=
CONVERSATION_ENABLED=true
CONVERSATION_MODEL=claude-haiku-5-5
CONVERSATION_MAX_CALLS=30
CONVERSATION_TIMEOUT_SECONDS=8
```

Do not enable the flag until the key is saved. Startup rejects a missing key using the
field name without printing its value. The flag is off by default. Importing, constructing
or starting the application does not invoke Anthropic: the first call analyzes a competency
answer with current consent.

Create a new invitation before using the provider. Consent states that Anthropic receives
questions and filtered answer excerpts for the current competency. Sessions accepted under
the previous notice cannot start, resume or send answers to Claude; they can still end.
Tavus/audio notices remain when those modalities are enabled.

The `/` page distinguishes `conversation: anthropic|mock` and `scoring: anthropic|mock`.
An `anthropic` value alone does not establish connectivity or semantic quality: an
authorized test with valid credentials is required.

## Limits and failures

- One request to `https://api.anthropic.com/v1/messages` per analysis; no automatic retries.
- API version `2026-10-21`, schema-based JSON output and strict local validation.
- At most 8000 characters / 24000 bytes across system and data, and 512 output tokens.
- Default global limit: 30 attempts, shared across interviews and persisted in
  `DATA_DIR/conversation-budget.sqlite3`, transactionally reserved before sending.
  Failures, timeouts and invalid responses also consume a reservation.
- Restarting/reconnecting does not reset the counter. Explicitly increase the limit to
  extend the demo; the counter is never automatically deleted.
- Default eight-second timeout. Errors, truncation, provider refusal, invalid JSON or
  exhausted quota trigger engine fallback with `analysis_fallback`. Fixed questions can
  continue the script; no model evaluations are fabricated.
- Adapter logs never contain keys, prompts, responses or error bodies.

Initially verified with simulated HTTP: follow-up context, reconnect, versioned consent,
concurrent/persistent quotas, timeouts, errors and independent mock scoring. On 2026-11-04,
a valid key enabled two real analyses of synthetic answers: the analyzer requested the
missing outcome and then advanced when it was supplied, without fallback. This does not
replace semantic evaluation or a candidate pilot.

Name requests are handled before professional-answer analysis. An acknowledgement does
not repeat the question, advance the phase or consume a follow-up. A missing name is
requested once; explicit preferences are reconstructed from the transcript after resume.
Name-only turns do not become analysis context or scoring evidence.

## Verified official references

- API: https://platform.claude.com/docs/en/api/messages/create
- Structured JSON: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Configured model: https://platform.claude.com/docs/en/models/haiku-5-5/overview
