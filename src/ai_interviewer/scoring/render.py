"""Render validated reports with sanitized citations and escaped output."""
from html import escape
from uuid import UUID

from ai_interviewer.contracts import InterviewReport, Turn
from ai_interviewer.engine.safety import safe_text


def _markdown(text: str) -> str:
    text = escape(text, quote=True)
    for char in ("\\", "`", "*", "_", "{", "}", "[", "]", "(", ")", "#", "+", "-", "!", "|"):
        text = text.replace(char, "\\" + char)
    return text.replace("\r", " ").replace("\n", " ")


def _evidence(report: InterviewReport, turns: list[Turn]) -> dict[UUID, str]:
    candidate = {turn.id: safe_text(turn.text) for turn in turns if turn.speaker == "candidate"}
    for score in report.scores:
        if any(not candidate.get(turn_id) for turn_id in score.evidence_turn_ids):
            raise ValueError("report citation missing from sanitized candidate transcript")
    return candidate


def render_markdown(report: InterviewReport, turns: list[Turn]) -> str:
    evidence = _evidence(report, turns)
    lines = ["# Interview report", "", _markdown(report.summary), "", _markdown(report.recommendation), "",
             "| Competency | Score | Spread | Rationale |", "| --- | --- | --- | --- |"]
    for item in report.scores:
        value = str(item.score) if item.score is not None else "insufficient_evidence"
        lines.append(f"| {_markdown(item.competency_id)} | {value} | {item.dispersion:g} | {_markdown(item.rationale)} |")
    lines += ["", "## Textual evidence", ""]
    for item in report.scores:
        for turn_id in item.evidence_turn_ids:
            lines.append(f"- {_markdown(item.competency_id)} / {turn_id}: {_markdown(evidence[turn_id])}")
    lines += ["", "## Flags", ""] + [f"- {_markdown(flag)}" for flag in report.flags]
    lines += ["", "## Questions for human review", ""] + [f"- {_markdown(question)}" for question in report.suggested_questions]
    return "\n".join(lines) + "\n"


def render_html(report: InterviewReport, turns: list[Turn], competency_names: dict[str, str] | None = None) -> str:
    evidence = _evidence(report, turns)
    names = competency_names or {}
    rows = "".join(f"<tr><td>{escape(names.get(item.competency_id, item.competency_id))}</td><td>{str(item.score) + ' / 5' if item.score is not None else 'Insufficient evidence'}</td><td>{item.dispersion:g}</td><td>{escape(item.rationale)}</td></tr>" for item in report.scores)
    citations = "".join(f"<section><h3>{escape(names.get(item.competency_id, item.competency_id))}</h3>" +
                        "".join(f'<blockquote>{escape(evidence[turn_id])}</blockquote><p class="muted">Turn {turn_id}</p>' for turn_id in item.evidence_turn_ids) + "</section>"
                        for item in report.scores if item.evidence_turn_ids)
    flags = "".join(f"<li>{escape(flag)}</li>" for flag in report.flags)
    questions = "".join(f"<li>{escape(question)}</li>" for question in report.suggested_questions)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Interview report</title>'
            '<style>body{font-family:system-ui,sans-serif;max-width:1080px;margin:32px auto;padding:24px;color:#172838;line-height:1.6}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #dce3e8;text-align:left;padding:12px;vertical-align:top}blockquote{margin:12px 0;background:#f2f5f8;border-left:3px solid #8da8b4;padding:16px;white-space:pre-wrap}.muted{color:#506575}.note{background:#edf5f9;padding:16px}section{break-inside:avoid}@media print{body{margin:0;padding:0;font-size:11px}}</style></head><body>'
            f'<h1>Interview report</h1><p class="note">Human review pending. Scores do not constitute a hiring decision.</p><p>{escape(report.summary)}</p><p>{escape(report.recommendation)}</p>'
            f'<p class="muted">Generated: {escape(report.generated_at.isoformat())} · Three evaluations per competency.</p>'
            '<table><thead><tr><th>Competency</th><th>Score</th><th>Spread</th><th>Rationale</th></tr></thead>'
            f'<tbody>{rows}</tbody></table><h2>Textual evidence</h2>{citations}'
            f'<details><summary>Validation details</summary><ul>{flags}</ul></details><h2>Questions for human review</h2><ul>{questions}</ul></body></html>')
