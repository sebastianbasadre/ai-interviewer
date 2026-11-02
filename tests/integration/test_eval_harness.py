import json
from pathlib import Path

import pytest

from ai_interviewer.engine.roles import load_role
from evals.latency_probe import LatencySample, percentile, summarize_latency
from evals.personas import load_personas
from evals.run_evals import Components, offline_components, run_evals, summarize, write_results

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def role():
    return load_role(ROOT / "roles/pm_po.yaml")


def test_persona_corpus_covers_required_adversaries(role):
    personas = load_personas(ROOT / "evals/personas", role)
    assert len(personas) >= 10
    tags = {tag for persona in personas for tag in persona.tags}
    assert {"ranking_strong", "ranking_average", "ranking_weak", "injection", "sensitive", "english_switch", "company_question", "verbose", "monosyllabic", "nervous", "evasive"} <= tags
    assert all(set(persona.expected_scores) == {c.id for c in role.competencies} for persona in personas)


@pytest.mark.asyncio
async def test_offline_corpus_has_structural_coverage_but_no_quality_pass(role, tmp_path):
    result = await run_evals(role, load_personas(ROOT / "evals/personas", role))
    assert len(result["sessions"]) >= 10
    assert result["summary"]["structural_failures"] == 0
    assert all(session["observations"]["completed"] for session in result["sessions"])
    assert all(session["observations"]["phase_coverage"] == 1 for session in result["sessions"])
    assert all(session["observations"]["competency_coverage"] == 1 for session in result["sessions"])
    assert all(session["observations"]["followup_limit_respected"] for session in result["sessions"])
    assert all(metric["status"] == "not_evaluated" for metric in result["summary"]["metrics"].values())
    assert not result["summary"]["all_quality_gates_passed"]
    assert all(all(score is None for score in session["scores"].values()) for session in result["sessions"])
    injection = next(session for session in result["sessions"] if session["persona_id"] == "injection")
    assert "injection_attempt" in injection["report"]["flags"]
    json_path, md_path = write_results(result, tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["mode"] == "offline"
    assert "not_evaluated" in md_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_real_mode_refuses_before_calling_factories(role):
    calls = []
    def forbidden():
        calls.append(True)
        raise AssertionError("provider must not be constructed")
    components = Components(forbidden, forbidden, forbidden, real_models=True)
    personas = load_personas(ROOT / "evals/personas", role)
    with pytest.raises(PermissionError):
        await run_evals(role, personas, components)
    assert calls == []


@pytest.mark.asyncio
async def test_limits_and_provider_errors_are_bounded_and_redacted(role):
    personas = load_personas(ROOT / "evals/personas", role)[:1]
    with pytest.raises(ValueError):
        await run_evals(role, personas, runs=11)
    components = offline_components()
    def broken():
        raise RuntimeError("do not echo confidential-provider-payload")
    components.engine_factory = broken
    result = await run_evals(role, personas, components)
    assert result["summary"]["structural_failures"] == 1
    assert "confidential-provider-payload" not in json.dumps(result)
    assert not result["summary"]["all_quality_gates_passed"]


def test_semantic_metrics_require_independent_auditor():
    session = {"quality_evaluation_valid": True, "tags": ["injection", "sensitive", "company_question"],
        "observations": {"phase_coverage": 1, "competency_coverage": 1, "missing_example_checks": []},
        "scores": {"discovery": 3}, "expected_scores": {"discovery": 3}, "dispersion": [0], "failures": []}
    result = summarize([session], real_models=True)
    for key in ("injection_resistance", "sensitive_content_absent", "company_facts_grounded"):
        assert result["metrics"][key]["status"] == "not_evaluated"
    assert not result["all_quality_gates_passed"]


def test_latency_uses_direct_total_percentile_and_rejects_mock_claims():
    assert percentile([100, 300, 500], .5) == 300
    samples = [LatencySample(real_services=True, stages_ms={"total": value, "stt": 100}) for value in [1000, 1100, 1300]]
    result = summarize_latency(samples, minimum_samples=3)
    assert result["target"]["status"] == "passed"
    assert result["stages"]["total"]["p50_ms"] == 1100
    assert summarize_latency(samples)["target"]["status"] == "not_evaluated"
    mock = [LatencySample(real_services=False, stages_ms={"total": 1})]
    assert summarize_latency(mock, minimum_samples=1)["target"]["status"] == "not_evaluated"


def test_latency_rejects_content_and_nonfinite_values():
    with pytest.raises(ValueError):
        LatencySample.model_validate({"real_services": True, "stages_ms": {"total": 10}, "transcript": "private"})
    with pytest.raises(ValueError):
        LatencySample(real_services=True, stages_ms={"total": float("nan")})
