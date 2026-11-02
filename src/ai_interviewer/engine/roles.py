"""Load explicitly selected, versioned role data without network access."""
from pathlib import Path

import yaml

from ai_interviewer.contracts import RoleSpec


def load_role(path: str | Path) -> RoleSpec:
    """Read a trusted role file selected by the application, never a user URL/path."""
    with Path(path).open(encoding="utf-8-sig") as role_file:
        data = yaml.safe_load(role_file)
    return RoleSpec.model_validate(data)
