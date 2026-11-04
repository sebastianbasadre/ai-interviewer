"""Structured scoring through the same bounded HTTP boundary as conversation."""
import json

from ai_interviewer.engine.anthropic import AnthropicJSONModel, ConversationModelError
from .scorer import ScoringRun


class AnthropicScoringModel(AnthropicJSONModel):
    max_input_chars = 50000
    max_input_bytes = 100000
    max_output_tokens = 4096

    def output_schema(self):
        properties = {
            "competency_id": {"type": "string"},
            "score": {"anyOf": [{"type": "integer"}, {"type": "null"}],
                      "description": "Entero de 1 a 5 con evidencia suficiente; null si falta evidencia."},
            "evidence_turn_ids": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
            "insufficient_evidence": {"type": "boolean"},
        }
        return {"type": "object", "additionalProperties": False, "required": ["scores"],
                "properties": {"scores": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": list(properties), "properties": properties}}}}

    def validate_result(self, result):
        parsed = ScoringRun.model_validate_json(json.dumps(result), strict=True)
        if any(len(score.rationale) > 1200 for score in parsed.scores):
            raise ConversationModelError("Scoring rationale exceeds its limit.")
        return parsed.model_dump_json()
