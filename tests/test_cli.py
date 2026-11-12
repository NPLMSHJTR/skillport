"""Tests for the CLI, especially the contract around destructive commands."""

from __future__ import annotations

import json
from pathlib import Path

from skillport.cli import main


def test_list_shows_targets_and_presets(capsys):
    assert main(["list", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "codex" in out
    assert "common" in out
    assert "reported" in out, "unverified paths must be labelled"


def test_list_warns_about_reported_paths(capsys):
    main(["list", "--no-color"])
    out = capsys.readouterr().out
    assert "community-reported" in out


def test_check_missing_exits_one(project: Path, capsys):
    assert main(["check", str(project), "--no-color"]) == 1
    assert "missing" in capsys.readouterr().out


def test_sync_then_check_exits_zero(project: Path, capsys):
    assert main(["sync", str(project)]) == 0
    capsys.readouterr()
    assert main(["check", str(project), "--no-color"]) == 0
    assert "in sync" in capsys.readouterr().out


def test_check_json_shape(project: Path, capsys):
    main(["check", str(project), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {
        "source", "skills", "targets", "in_sync", "missing", "drifted", "extra"
    }
    assert payload["skills"] == ["example-review"]
    assert len(payload["missing"]) == len(payload["targets"])


def test_sync_dry_run_writes_nothing(project: Path, capsys):
    assert main(["sync", str(project), "--dry-run"]) == 0
    assert "would sync" in capsys.readouterr().out
    assert not (project / ".codex").exists()


def test_sync_missing_source_exits_two(tmp_path: Path, capsys):
    assert main(["sync", str(tmp_path)]) == 2
    assert "source directory not found" in capsys.readouterr().err


def test_check_missing_source_exits_two(tmp_path: Path, capsys):
    assert main(["check", str(tmp_path)]) == 2
    assert "source directory not found" in capsys.readouterr().err


def test_prune_without_yes_refuses(project: Path, capsys):
    main(["sync", str(project)])
    stray = project / ".codex" / "skills" / "stray"
    stray.mkdir()
    (stray / "SKILL.md").write_text("---\nname: stray\n---\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["prune", str(project)]) == 2
    assert "re-run with --yes" in capsys.readouterr().err
    assert stray.exists(), "nothing may be deleted without --yes"


def test_prune_with_yes_deletes(project: Path, capsys):
    main(["sync", str(project)])
    stray = project / ".codex" / "skills" / "stray"
    stray.mkdir()
    (stray / "SKILL.md").write_text("---\nname: stray\n---\n", encoding="utf-8")
    capsys.readouterr()

    assert main(["prune", str(project), "--yes"]) == 0
    assert not stray.exists()


def test_prune_nothing_to_do(project: Path, capsys):
    main(["sync", str(project)])
    capsys.readouterr()
    assert main(["prune", str(project), "--yes"]) == 0
    assert "nothing to prune" in capsys.readouterr().out


def test_explicit_target_accepted(project: Path, capsys):
    assert main(["sync", str(project), "--target", "codex"]) == 0
    assert (project / ".codex" / "skills" / "example-review" / "SKILL.md").exists()
    assert not (project / ".claude").exists()


def test_multiple_target_flags(project: Path, capsys):
    assert main([
        "sync", str(project), "--target", "codex", "--target", "claude"
    ]) == 0
    assert (project / ".codex").exists()
    assert (project / ".claude").exists()


def test_unknown_target_exits_with_message(project: Path, capsys):
    try:
        code = main(["sync", str(project), "--target", "nope"])
    except ValueError as exc:
        assert "unknown target" in str(exc)
    else:
        raise AssertionError("expected a ValueError or handled error")