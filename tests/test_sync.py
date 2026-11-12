"""Tests for check / sync / prune, including the dangerous parts."""

from __future__ import annotations

from pathlib import Path

from skillport.sync import check, discover_skills, prune, sync
from skillport.targets import PRESETS, resolve


def test_discover_finds_skills(project: Path):
    skills = discover_skills(project / "skills")
    assert [s.name for s in skills] == ["example-review"]


def test_discover_ignores_hidden(project: Path):
    hidden = project / "skills" / ".hidden" / "SKILL.md"
    hidden.parent.mkdir(parents=True)
    hidden.write_text("---\nname: x\n---\n", encoding="utf-8")
    names = [s.name for s in discover_skills(project / "skills")]
    assert ".hidden" not in names


def test_check_reports_missing_before_sync(project: Path):
    report = check(project, project / "skills", PRESETS["common"])
    assert len(report.missing) == len(PRESETS["common"].targets)
    assert report.drifted == []
    assert report.has_problems


def test_sync_then_check_is_clean(project: Path):
    sync(project, project / "skills", PRESETS["common"])
    report = check(project, project / "skills", PRESETS["common"])
    assert not report.has_problems
    assert len(report.in_sync) == len(PRESETS["common"].targets)


def test_sync_copies_nested_files(project: Path):
    sync(project, project / "skills", resolve(["codex"]))
    copied = project / ".codex" / "skills" / "example-review" / "references" / "guide.md"
    assert copied.exists()


def test_sync_twice_is_idempotent(project: Path):
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    first = check(project, project / "skills", targets)
    sync(project, project / "skills", targets)
    second = check(project, project / "skills", targets)
    assert first.has_problems == second.has_problems is False


def test_drift_detected_after_editing_source(project: Path):
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    (project / "skills" / "example-review" / "SKILL.md").write_text(
        "# Changed\n\nnew instruction\n", encoding="utf-8"
    )
    report = check(project, project / "skills", targets)
    assert len(report.drifted) == 1
    _, _, changed = report.differences[("codex", "example-review")]
    assert "SKILL.md" in changed


def test_drift_detected_after_editing_target(project: Path):
    """Editing the copy is the mistake this tool exists to catch."""
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    copy = project / ".codex" / "skills" / "example-review" / "SKILL.md"
    copy.write_text("# Edited in place\n", encoding="utf-8")
    report = check(project, project / "skills", targets)
    assert len(report.drifted) == 1


def test_extra_skill_detected(project: Path):
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    stray = project / ".codex" / "skills" / "stray"
    stray.mkdir()
    (stray / "SKILL.md").write_text("---\nname: stray\n---\n", encoding="utf-8")
    report = check(project, project / "skills", targets)
    assert [s.skill_name for s in report.extra] == ["stray"]


def test_extra_directory_without_skill_md_ignored(project: Path):
    """A stray folder that is not a skill is not ours to report or delete."""
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    (project / ".codex" / "skills" / "notaskill").mkdir()
    report = check(project, project / "skills", targets)
    assert report.extra == []


def test_prune_removes_only_orphan_skills(project: Path):
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    stray = project / ".codex" / "skills" / "stray"
    stray.mkdir()
    (stray / "SKILL.md").write_text("---\nname: stray\n---\n", encoding="utf-8")
    keep = project / ".codex" / "skills" / "notaskill"
    keep.mkdir()

    removed = prune(project, project / "skills", targets)
    assert [p.name for p in removed] == ["stray"]
    assert not stray.exists()
    assert keep.exists(), "a directory without SKILL.md must not be deleted"
    assert (project / ".codex" / "skills" / "example-review").exists()


def test_prune_keeps_skills_still_in_source(project_two_skills: Path):
    targets = resolve(["codex"])
    sync(project_two_skills, project_two_skills / "skills", targets)
    removed = prune(project_two_skills, project_two_skills / "skills", targets)
    assert removed == []


def test_sync_only_named_skill(project_two_skills: Path):
    targets = resolve(["codex"])
    written = sync(
        project_two_skills, project_two_skills / "skills", targets, only=["changelog"]
    )
    assert len(written) == 1
    assert written[0].name == "changelog"
    assert not (project_two_skills / ".codex" / "skills" / "example-review").exists()


def test_sync_replaces_stale_files(project: Path):
    """A file deleted in the source must not survive in the target."""
    targets = resolve(["codex"])
    sync(project, project / "skills", targets)
    stale = project / ".codex" / "skills" / "example-review" / "old.md"
    stale.write_text("old\n", encoding="utf-8")
    sync(project, project / "skills", targets)
    assert not stale.exists()


def test_multiple_targets_all_synced(project: Path):
    targets = resolve(["codex", "claude"])
    sync(project, project / "skills", targets)
    for directory in (".codex/skills", ".claude/skills"):
        assert (project / directory / "example-review" / "SKILL.md").exists()


def test_unknown_target_raises():
    try:
        resolve(["notarealagent"])
    except ValueError as exc:
        assert "unknown target" in str(exc)
    else:
        raise AssertionError("expected ValueError")