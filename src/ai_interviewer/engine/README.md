# Pilot engine and scoring

`StructuredInterviewEngine` implements the async contract. Each instance represents one
interview; `start()` assumes persisted consent. `transcript()` includes both speakers with
stable IDs. Persist decisions and their flags before emitting audio. The engine does not
write storage or start services.

Without adapters, `OfflineAnswerAnalyzer` conservatively requests STAR clarification up
to the limit without pretending to perform semantic evaluation. For an LLM, inject
`LLMAnswerAnalyzer(model)` and optionally `LLMQuestionWriter(model)`. Providers implement
`async complete(system: str, user: str) -> str` returning JSON. The application controls
credentials, budget and transport. Importing modules never makes network calls.

The text demo enables `mock_single_followup`: ask once for clarification, then advance
with `mock_script_advance` without claiming sufficient evidence. Progress survives restore.
This mode does not modify LLM analyzers.

For pilot safety, writer output must exactly match an approved question for the current
competency. Other wording falls back to the base question with `question_fallback`.
This restricts paraphrasing until semantic evaluation is available. Code always controls
phases, termination, repeats and time limits.

`restore()` assumes the API checked credentials, UUID, role/version and candidate binding
to the stored Interview. SessionSnapshot does not contain those attributes. The engine
checks timestamps, competencies, original deadline and state without speaking again.
Preserve the monotonic turn clock's origin across reconnects.

`InterviewScorer(model).score(interview_id, role, turns, flags=None)` runs three bounded
evaluations. It rejects references outside candidate answers for the competency (except
cross-competency communication), sensitive output and hiring decisions. If any run lacks
evidence, leave the final score unnumbered. With three numbers, use the median and
maximum-minus-minimum spread. Model evaluation and human review establish citation
relevance; IDs and keywords alone cannot.

`MockScoringModel` is an explicit offline provider: all scores remain unnumbered and
reports carry `mock_scoring`. It does not measure candidate quality.

`safe_text` excludes sentences matching sensitive patterns and turns containing malicious
instructions. This conservative lexical defense does not guarantee detection of all
sensitive information, inference or indirect injection. Prompts reinforce the prohibitions.
Real evaluations, privacy review and human calibration are prerequisites to a pilot;
unit tests do not establish that semantic safeguards are solved. Preserve raw transcripts
in authorized storage; never print or send the complete raw transcript to scoring.

The scorer reconstructs `injection_attempt` from the transcript so it survives resume.
The API must separately persist other decision, cutoff and degradation flags and pass
them to the scorer; SessionSnapshot does not contain them.

Name requests are handled separately from professional answers. They acknowledge the
preferred name without repeating the question, advancing the phase or consuming follow-ups.
Preferences and the pending question survive restore. Name-only turns are excluded from
answer analysis and scoring evidence.
