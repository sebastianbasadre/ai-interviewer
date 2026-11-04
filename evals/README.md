# Synthetic evaluations and integration tests

Status: offline tooling implemented; **G3 pending**. No real-model evaluation batch has
been run. Profiles are synthetic fixtures; expected levels are calibration hypotheses
for human review, not objective truth.

## Offline usage without costs

From the repository root, with Python 3.12 and test dependencies:

```bash
python -m evals.run_evals
python -m evals.run_evals --runs 3 --output evals/results
python -m pytest tests/integration
```

The default uses `StructuredInterviewEngine` without an LLM, scripted answers and
`MockScoringModel`. It exercises real phase, follow-up, flag and scoring code, but the
offline analyzer requests conservative clarifications and scoring returns only null
scores with `mock_scoring`. **This does not measure conversation quality, ranking or accuracy.**
Every quality gate is `not_evaluated`; passing mocks never authorizes a pilot. JSON
separates structural observations from metrics: flow coverage, limits, termination,
follow-ups for fixtures without examples, and synthetic sensitive-data canaries.
Markdown reports list failures by persona/turn; JSON retains synthetic transcripts for
evidence investigation.

There are eleven profiles: strong, average, weak, evasive, verbose, monosyllabic, hesitant,
injection, sensitive data, English switching, and salary/benefits questions.
`expected_scores: null` means the profile cannot establish a reference score, not that
it deserves 1. The verbose fixture's three-minute duration is an annotation, not audio
or measured latency.

## Injecting real services (after G3)

A trusted factory must return `Components` from `evals.run_evals` with:

- A new engine per session with the real provider's analyzer/writer configured.
- A candidate responder that receives the profile and produces `Answer` with bounded context.
- A new scorer per session using the large model and the real scorer's three runs.
- `real_models=True` and a description of the models/configuration used.
- An independent compliance/grounding auditor returning booleans or `None` for
  `injection_resistance`, `sensitive_content_absent`, `company_facts_grounded`.

```bash
python -m evals.run_evals --factory trusted_package:components --allow-paid --runs 3
```

`--allow-paid` represents explicit owner approval; never add it in a Makefile or defaults.
Without the flag, the real factory is not even imported. The real factory is not provided
as automatic provider activation. The runner limits execution to 100 sessions, ten repeats,
64 turns per session and a 600-second per-session timeout. This is not a dollar limit:
the factory must reserve budget before every call, bound tokens/retries and record usage
without content or keys.

Coverage/follow-up checks are computed automatically, but establishing quality requires
a real engine. Ranking, expected agreement and spread are calculated only with real
scoring, never mock scores. Sensitive-language checks, prompt leakage and invented facts
need independent semantic auditing; canaries and keywords cannot replace it. Injection
also requires comparing a professional baseline with the same attacked example and
checking that scores do not change and instructions are not disclosed. The factory/auditor
must supply this evidence or return `None`. Without an auditor or sufficient evidence,
the gate remains `not_evaluated`. An injection-only profile must have no numeric score;
it does not independently establish invariance in mixed professional/attack cases.

Real results may contain generated text and are stored in gitignored `evals/results/`.
Use only synthetic data; never point the harness at real transcripts. Log provider
exception types, not text that might contain secrets.

## Latency

`latency_probe.py` aggregates real-service samples; it does not invent measurements.
Input is JSONL, one sample per turn, without audio, text or personal data:

```json
{"real_services": true, "stages_ms": {"vad": 200, "stt": 200, "llm_ttfb": 300, "tts_ttfb": 250, "avatar": 200, "total": 1150}}
```

This illustrates the format, **not a system result**.

```bash
python -m evals.latency_probe /path/to/measured-latencies.jsonl
```

Reports per-stage and total p50/p95. Measure total time from the end of candidate speech
to first avatar/output audio with the same monotonic clock; do not sum stage percentiles.
Evaluate the p50 <1200 ms target only with at least 30 real samples. Mock/insufficient
samples return `not_evaluated`. Content fields and negative/nonfinite values are rejected.
No real sample set or validated latency exists yet.

## G3 proposal (not executed)

First batch: **11 profiles × 3 repeats = 33 text conversations**, with three scoring runs
per conversation (99 large-model calls) and one independent audit per session (33 large
calls, plus baseline/attack comparisons where needed). No STT/TTS/Tavus. Start with a
one-session smoke within the same budget to check JSON/usage. If it fails, stop rather
than retrying the batch. At most three fix iterations before escalating the diagnosis;
every additional batch requires an explicit budget.

Configured IDs `claude-haiku-5-5` and `claude-opus-5-5` were listed in the
[official catalog](https://platform.claude.com/docs/en/models/overview), checked on
2026-11-02. Standard prices checked then: Haiku 5.5 USD 0.10/MTok input and 0.50/MTok
output for prompts up to 100k tokens; Opus 5.5 USD 4/MTok input and 20/MTok output.
Source: [official pricing documentation](https://platform.claude.com/docs/en/about-claude/pricing).
Verify actual account availability, prices and credentials before the smoke test.

Scenario estimate, **not measured usage or a billing guarantee**:

| Work per conversation | Input tokens | Output tokens | USD cost |
| --- | ---: | ---: | ---: |
| Up to 70 Haiku calls (candidate + analyzer + writer), average 1500/300 tokens | 105000 | 21000 | 0.021 |
| Three Opus scoring runs, 15000/1500 tokens each | 45000 | 4500 | 0.270 |
| Opus auditor, 15000/1000 tokens | 15000 | 1000 | 0.080 |
| Estimated total per conversation | | | 0.371 |
| 33 conversations | | | 12.243 |

Formula: `(input × input_rate + output × output_rate) / 1_000_000`, summed per model/call.
A 50% margin gives approximately **USD 18.40**. Proposed cap: **USD 20** for the batch,
including smoke and injection comparisons. Do not guarantee all 33 sessions if budget
runs out; stop before the next call. Thinking, retries, extra auditing and longer context
consume budget. Do not assume Batch/cache discounts, included taxes or fictitious token
limits. Monetary controls and the real adapter must exist and be tested before using the flag.

G3 prerequisites: owner approval with a cap, audited real factory, credentials configured
without printing them, bounded tokens/retries and budget reservation, and baseline/attack
comparison evidence to establish injection resistance.
