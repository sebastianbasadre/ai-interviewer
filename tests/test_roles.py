from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_interviewer.engine.roles import load_role


ROLE_PATH = Path(__file__).resolve().parents[1] / "roles" / "pm_po.yaml"


def test_pm_po_role_has_reviewable_competencies_and_alternative_questions():
    role = load_role(ROLE_PATH)
    assert role.id == "pm_po"
    assert role.target_minutes == 25
    assert role.max_followups == 2
    assert {item.id for item in role.competencies} == {
        "discovery", "prioritization", "metrics_outcomes",
        "stakeholders", "execution", "communication",
    }
    assert [item.id for item in role.competencies if item.transversal] == ["communication"]
    question_ids = [question.id for item in role.competencies for question in item.questions]
    assert len(set(question_ids)) == len(question_ids)
    for competency in role.competencies:
        assert {anchor.score for anchor in competency.anchors} == {1, 3, 5}
        for question in competency.questions:
            assert question.followup_criteria
            assert any("case" in criterion or "example" in criterion for criterion in question.followup_criteria)


def test_unknown_company_information_is_not_invented():
    assert load_role(ROLE_PATH).company_info == {}


def test_loader_rejects_invalid_role_contract(tmp_path):
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("id: pm_po\ncompetencies: []\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_role(invalid)


def test_loader_uses_safe_yaml(tmp_path):
    unsafe = tmp_path / "unsafe.yaml"
    unsafe.write_text("!!python/object/apply:builtins.print ['unsafe']", encoding="utf-8")
    import yaml
    with pytest.raises(yaml.constructor.ConstructorError):
        load_role(unsafe)
