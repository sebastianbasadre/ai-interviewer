# Evidence-based reports and human review

## Usage

Open `https://192.168.2.6:8443/admin/review` and enter `ADMIN_API_KEY` from `.env`.
The key remains in browser memory until logout/reload, never localStorage, cookies or
URLs. The login page is public, but the list, reports, citations and HTML download
require the `X-Admin-Key` header.

The list shows interviews and report status. With automatic generation enabled, normal
closure starts a background job. The interview ends immediately; evaluation appears
when all three runs complete. Generate/retry completed-interview reports from the list.
Retrying can consume another three evaluations; requesting an already stored report
returns the existing result without another provider call.

Each competency displays a 1–5 score or **Insufficient evidence**, rationale, verbatim
citations from filtered excerpts and the spread across three evaluations. Expand rubric
anchors to compare scores. Reports remain pending human review and never make hiring
decisions. The standalone HTML download escapes candidate/model content.

## Evaluation

`SCORING_ENABLED=true` uses Claude Opus 5.5 with the approved rubric and filtered
professional transcript. It excludes candidate profiles, audio, video and company_info.
Sanitization is conservative and lexical; it cannot guarantee anonymization of arbitrary
free text. Validate all six competencies, integer scores 1–5 and references to actual
candidate turns. Each citation must belong to the competency, except Communication,
which accepts evidence across competencies. Unknown IDs, interviewer turns, duplicates
and excluded content cannot justify a score.

Run three evaluations. If any finds insufficient evidence, leave the final score `null`;
never automatically turn it into 1. With three valid numbers, use the median together
with that evaluation's rationale/citations. Flag differences greater than one point.
Never publish a partial report without three valid evaluations.

This validates structure and references, not semantic relevance, calibration or absence
of bias. The retained example is entirely synthetic, not an evaluation of a real person.

## Configuration

```dotenv
ANTHROPIC_API_KEY=
SCORING_ENABLED=true
SCORING_MODEL=claude-opus-5-5
SCORING_AUTO_GENERATE=true
SCORING_MAX_CALLS=12
SCORING_TIMEOUT_SECONDS=45
```

Requires the HTTPX-based `llm` extra. The template leaves the flag disabled by default.
`APP_MODE=mock` retains the demo engine; `/` distinguishes conversation/scoring providers
separately. Constructing or starting the app does not call Opus.

Each report atomically reserves three attempts in `DATA_DIR/scoring-budget.sqlite3`.
The global limit persists across interviews, reconnects and restarts. No automatic retries.
Failures, cancellations and schema rejections also consume conservative reservations.
The model receives at most 50000 characters / 100000 bytes of context and generates at
most 4096 tokens per run. These bounds are not a monetary budget.

Missing keys cause startup rejection naming the field. Errors/invalid output leave a
failed job requiring explicit retry. On restart, interrupted jobs become failed rather
than being automatically billed again. Stored reports survive. Deleting an interview
also deletes its report/job status; the global usage counter is retained and contains
no personal data.

## Consent and privacy

Enabling scoring adds an explicit notice: Anthropic receives the rubric and transcript
excerpts to propose scores with citations for human review. Create a new invitation
after enabling it. The previous mock-scoring notice does not authorize real evaluation;
start/resume/answer submission or real report generation with that consent is rejected.
Existing mock reports remain labeled historical records. Candidates can end old sessions
without authorizing real scoring.

## Endpoints

- `GET /admin/review`: login and review shell; contains no private data.
- `GET /admin/interviews`: authenticated list, session/report status, scoring mode.
- `POST /admin/interviews/{id}/report`: generate or return the existing report.
- `GET /admin/interviews/{id}/report`: validated JSON.
- `GET /admin/interviews/{id}/review`: report, filtered citations and rubric for the UI.
- `GET /admin/interviews/{id}/report.html`: authenticated download for human review.

## Real verification — 2026-11-04

Used `evals/report_fixture.py`: six competencies, deliberately omitting a Metrics example.
Opus left Metrics null and cited existing evidence for the five numeric scores. Three
runs completed in approximately 33 seconds. A nullable-score enum API rejection was
fixed using anyOf and strict local range validation. No Tavus sessions were used.
Chrome verification: six competencies, seven citations and six rubrics; valid HTML
download, logout and zero JavaScript errors. Final suite at that checkpoint: 140 tests.

Model/pricing source: https://platform.claude.com/docs/en/models/opus-5-5/overview.
Structured JSON: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.
