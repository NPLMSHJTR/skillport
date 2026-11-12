"""Sync skills from a single source directory to each agent's location.

Three operations:

    sync    copy the source into each target, replacing what is there
    check   report drift without writing anything
    prune   remove files in a target that no longer exist in the source

The ordering matters. `check` runs in CI and must never write. `sync` is the fix
a developer runs locally. `prune` is separate because deleting files is the one
operation that can lose work, so it never happens implicitly.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .fingerprint import Fingerprint, fingerprint
from .targets import Target, TargetSet


@dataclass
class Skill:
    name: str
    source: Path
    fingerprint: Fingerprint


@dataclass
class TargetState:
    """What a target directory currently holds for one skill."""

    target: Target
    skill_name: str
    destination: Path
    exists: bool
    fingerprint: Fingerprint | None


@dataclass
class CheckReport:
    skills: list[str] = field(default_factory=list)
    in_sync: list[TargetState] = field(default_factory=list)
    missing: list[TargetState] = field(default_factory=list)
    drifted: list[TargetState] = field(default_factory=list)
    extra: list[TargetState] = field(default_factory=list)
    # Per-state detail for the drifted entries, keyed by (target, skill).
    differences: dict[tuple[str, str], tuple[list[str], list[str], list[str]]] = field(
        default_factory=dict
    )

    @property
    def has_problems(self) -> bool:
        return bool(self.missing or self.drifted or self.extra)


def discover_skills(source_root: Path) -> list[Skill]:
    """Find skill directories under the source root.

    A skill is any directory containing a SKILL.md, at any depth, so both
    `skills/<name>/SKILL.md` and a flat `skills/SKILL.md` work.
    """
    if not source_root.is_dir():
        return []
    skills: list[Skill] = []
    for skill_md in sorted(source_root.rglob("SKILL.md")):
        if any(part.startswith(".") for part in skill_md.relative_to(source_root).parts):
            continue
        directory = skill_md.parent
        skills.append(
            Skill(
                name=directory.name,
                source=directory,
                fingerprint=fingerprint(directory),
            )
        )
    return skills


def _copy_skill(source: Path, destination: Path) -> None:
    """Replace destination with a clean copy of source."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo", ".DS_Store", "Thumbs.db"
        ),
    )


def check(project_root: Path, source_root: Path, target_set: TargetSet) -> CheckReport:
    """Compare the source against every target. Reads only; never writes."""
    report = CheckReport()
    skills = discover_skills(source_root)
    report.skills = [s.name for s in skills]

    for target in target_set.targets:
        base = project_root / target.directory
        for skill in skills:
            destination = base / skill.name
            state = TargetState(
                target=target,
                skill_name=skill.name,
                destination=destination,
                exists=destination.is_dir(),
                fingerprint=None if not destination.is_dir() else fingerprint(destination),
            )

            if not state.exists:
                report.missing.append(state)
                continue

            if state.fingerprint is None or state.fingerprint.digest != skill.fingerprint.digest:
                report.drifted.append(state)
                if state.fingerprint is not None:
                    report.differences[(target.name, skill.name)] = (
                        skill.fingerprint.differing_paths(state.fingerprint)
                    )
                continue

            report.in_sync.append(state)

        # Skills present in the target but absent from the source.
        if base.is_dir():
            source_names = {s.name for s in skills}
            for child in sorted(base.iterdir()):
                if not child.is_dir() or child.name in source_names:
                    continue
                if not (child / "SKILL.md").exists():
                    continue
                report.extra.append(
                    TargetState(
                        target=target,
                        skill_name=child.name,
                        destination=child,
                        exists=True,
                        fingerprint=fingerprint(child),
                    )
                )

    return report


def sync(
    project_root: Path,
    source_root: Path,
    target_set: TargetSet,
    only: list[str] | None = None,
) -> list[Path]:
    """Copy every skill into every target. Returns the paths written."""
    written: list[Path] = []
    for skill in discover_skills(source_root):
        if only and skill.name not in only:
            continue
        for target in target_set.targets:
            destination = project_root / target.directory / skill.name
            _copy_skill(skill.source, destination)
            written.append(destination)
    return written


def prune(
    project_root: Path,
    source_root: Path,
    target_set: TargetSet,
) -> list[Path]:
    """Delete skill directories in targets that no longer exist in the source.

    Only removes directories that contain a SKILL.md, so an unrelated folder that
    happens to live under a target path is left alone. This is the conservative
    half of the operation: it will miss things before it will delete something
    it should not.
    """
    removed: list[Path] = []
    source_names = {s.name for s in discover_skills(source_root)}
    for target in target_set.targets:
        base = project_root / target.directory
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name in source_names:
                continue
            if not (child / "SKILL.md").exists():
                continue
            shutil.rmtree(child)
            removed.append(child)
    return removed