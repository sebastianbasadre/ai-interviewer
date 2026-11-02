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
    lines = ["# Reporte de entrevista", "", _markdown(report.summary), "", _markdown(report.recommendation), "",
             "| Competencia | Score | Dispersión | Fundamentación |", "| --- | --- | --- | --- |"]
    for item in report.scores:
        value = str(item.score) if item.score is not None else "insufficient_evidence"
        lines.append(f"| {_markdown(item.competency_id)} | {value} | {item.dispersion:g} | {_markdown(item.rationale)} |")
    lines += ["", "## Evidencia textual", ""]
    for item in report.scores:
        for turn_id in item.evidence_turn_ids:
            lines.append(f"- {_markdown(item.competency_id)} / {turn_id}: {_markdown(evidence[turn_id])}")
    lines += ["", "## Flags", ""] + [f"- {_markdown(flag)}" for flag in report.flags]
    lines += ["", "## Preguntas para revisión humana", ""] + [f"- {_markdown(question)}" for question in report.suggested_questions]
    return "\n".join(lines) + "\n"


def render_html(report: InterviewReport, turns: list[Turn]) -> str:
    evidence = _evidence(report, turns)
    rows = "".join(f"<tr><td>{escape(item.competency_id)}</td><td>{item.score if item.score is not None else 'insufficient_evidence'}</td><td>{item.dispersion:g}</td><td>{escape(item.rationale)}</td></tr>" for item in report.scores)
    citations = "".join(f"<li>{escape(item.competency_id)} / {turn_id}: <q>{escape(evidence[turn_id])}</q></li>" for item in report.scores for turn_id in item.evidence_turn_ids)
    flags = "".join(f"<li>{escape(flag)}</li>" for flag in report.flags)
    questions = "".join(f"<li>{escape(question)}</li>" for question in report.suggested_questions)
    return ('<!doctype html><html lang="es"><meta charset="utf-8"><title>Reporte de entrevista</title>'
            f'<h1>Reporte de entrevista</h1><p>{escape(report.summary)}</p><p>{escape(report.recommendation)}</p>'
            '<table><thead><tr><th>Competencia</th><th>Score</th><th>Dispersión</th><th>Fundamentación</th></tr></thead>'
            f'<tbody>{rows}</tbody></table><h2>Evidencia textual</h2><ul>{citations}</ul>'
            f'<h2>Flags</h2><ul>{flags}</ul><h2>Preguntas para revisión humana</h2><ul>{questions}</ul></html>')
