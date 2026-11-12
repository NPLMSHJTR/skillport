"""Tests for the fingerprint, which is what makes drift detection possible."""

from __future__ import annotations

from pathlib import Path

from skillport.fingerprint import fingerprint


def _skill(root: Path, name: str = "s") -> Path:
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_same_content_same_digest(tmp_path: Path):
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    for d in (a, b):
        (d / "SKILL.md").write_text("# Same\n", encoding="utf-8")
    assert fingerprint(a).digest == fingerprint(b).digest


def test_line_endings_do_not_matter(tmp_path: Path):
    """A Windows checkout and a Linux checkout are the same skill."""
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    (a / "SKILL.md").write_bytes(b"# Title\nline one\nline two\n")
    (b / "SKILL.md").write_bytes(b"# Title\r\nline one\r\nline two\r\n")
    assert fingerprint(a).digest == fingerprint(b).digest


def test_trailing_whitespace_does_not_matter(tmp_path: Path):
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    (a / "SKILL.md").write_text("# Title\nbody\n", encoding="utf-8")
    (b / "SKILL.md").write_text("# Title   \nbody\t\n", encoding="utf-8")
    assert fingerprint(a).digest == fingerprint(b).digest


def test_real_content_change_changes_digest(tmp_path: Path):
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    (a / "SKILL.md").write_text("# Title\nbody one\n", encoding="utf-8")
    (b / "SKILL.md").write_text("# Title\nbody two\n", encoding="utf-8")
    assert fingerprint(a).digest != fingerprint(b).digest


def test_manifest_differences_are_ignored(tmp_path: Path):
    """Packaging files legitimately differ per target and must not cause drift."""
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    for d in (a, b):
        (d / "SKILL.md").write_text("# Same\n", encoding="utf-8")
    (a / "plugin.json").write_text('{"name": "a"}', encoding="utf-8")
    (b / "plugin.json").write_text('{"name": "b", "extra": true}', encoding="utf-8")
    assert fingerprint(a).digest == fingerprint(b).digest


def test_extra_file_changes_digest(tmp_path: Path):
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    for d in (a, b):
        (d / "SKILL.md").write_text("# Same\n", encoding="utf-8")
    (b / "extra.md").write_text("extra\n", encoding="utf-8")
    assert fingerprint(a).digest != fingerprint(b).digest


def test_differing_paths_reports_what_changed(tmp_path: Path):
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    (a / "SKILL.md").write_text("# Title\none\n", encoding="utf-8")
    (b / "SKILL.md").write_text("# Title\ntwo\n", encoding="utf-8")
    (a / "only-a.md").write_text("x\n", encoding="utf-8")
    (b / "only-b.md").write_text("y\n", encoding="utf-8")

    only_a, only_b, changed = fingerprint(a).differing_paths(fingerprint(b))
    assert "only-a.md" in only_a
    assert "only-b.md" in only_b
    assert "SKILL.md" in changed


def test_pycache_is_ignored(tmp_path: Path):
    a = _skill(tmp_path, "a")
    b = _skill(tmp_path, "b")
    for d in (a, b):
        (d / "SKILL.md").write_text("# Same\n", encoding="utf-8")
    cache = b / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"\x00\x01")
    assert fingerprint(a).digest == fingerprint(b).digest


def test_missing_directory(tmp_path: Path):
    assert fingerprint(tmp_path / "nope").digest == "missing"