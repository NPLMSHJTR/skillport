"""Shared fixtures: a project with a source skill and some targets."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

SKILL_MD = """---
name: example-review
description: Reviews a diff for risky changes. Use when the user asks for a review.
---

# Example review

Look at the diff and report the riskiest change first.
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with one skill in skills/ and no targets yet."""
    skill = tmp_path / "skills" / "example-review"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (skill / "references").mkdir()
    (skill / "references" / "guide.md").write_text(
        "# Guide\n\nSee the checklist.\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def project_two_skills(project: Path) -> Path:
    second = project / "skills" / "changelog"
    second.mkdir(parents=True)
    (second / "SKILL.md").write_text(
        textwrap.dedent(
            """\
            ---
            name: changelog
            description: Writes release notes. Use when the user asks for a changelog.
            ---

            # Changelog

            Group commits and write the section.
            """
        ),
        encoding="utf-8",
    )
    return project