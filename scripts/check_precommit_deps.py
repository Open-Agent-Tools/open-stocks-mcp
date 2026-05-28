#!/usr/bin/env python3
"""Verify .pre-commit-config.yaml mypy additional_dependencies match pyproject.toml.

Run via pre-commit or directly:
    python scripts/check_precommit_deps.py
"""

import re
import sys
import tomllib
from pathlib import Path

import yaml


def _normalize_name(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def _parse_spec(spec: str) -> tuple[str, str]:
    """Split 'pkg>=1.0' into (normalized_name, '>=1.0')."""
    match = re.match(r"^([A-Za-z0-9_.\-]+)(.*)", spec.strip())
    if not match:
        return spec.strip(), ""
    return _normalize_name(match.group(1)), match.group(2).strip()


def _load_pyproject_deps(root: Path) -> dict[str, str]:
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return dict(_parse_spec(s) for s in data["project"]["dependencies"])


def _load_precommit_mypy_deps(root: Path) -> dict[str, str]:
    with open(root / ".pre-commit-config.yaml") as f:
        config = yaml.safe_load(f)
    for repo in config.get("repos", []):
        for hook in repo.get("hooks", []):
            if hook.get("id") == "mypy":
                return dict(
                    _parse_spec(s) for s in hook.get("additional_dependencies", [])
                )
    return {}


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    pyproject = _load_pyproject_deps(root)
    precommit = _load_precommit_mypy_deps(root)

    errors: list[str] = []
    for name, pyproject_constraint in pyproject.items():
        if name not in precommit:
            continue  # package not listed in pre-commit (e.g. not needed for mypy)
        pc_constraint = precommit[name]
        if pc_constraint != pyproject_constraint:
            errors.append(
                f"  {name}: pre-commit={pc_constraint!r}  pyproject.toml={pyproject_constraint!r}"
            )

    if errors:
        print(
            "ERROR: .pre-commit-config.yaml mypy additional_dependencies "
            "drift from pyproject.toml:\n"
        )
        for line in errors:
            print(line)
        print(
            "\nSync the version constraints to match pyproject.toml.\n"
            "See CONTRIBUTING.md for details."
        )
        return 1

    print("OK: pre-commit mypy additional_dependencies match pyproject.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
