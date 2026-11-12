"""Command line interface.

    skillport check   [--target common] [--source skills]
    skillport sync    [--target common] [--skill name]
    skillport prune   [--target common] [--yes]
    skillport list

Exit codes:
    0  success / everything in sync
    1  check found drift or missing skills
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .sync import check, discover_skills, prune, sync
from .targets import PRESETS, TARGETS, resolve


def _paint(text: str, code: str, disabled: bool) -> str:
    return text if disabled else f"\033[{code}m{text}\033[0m"


def cmd_list(args: argparse.Namespace) -> int:
    no_color = args.no_color
    print(_paint("targets", "1", no_color))
    for name, target in sorted(TARGETS.items()):
        marker = _paint("verified", "32", no_color) if target.confidence == "verified" else _paint("reported", "33", no_color)
        print(f"  {name:10s} {target.directory:20s} {marker}")
        if target.note:
            print(f"             {_paint(target.note, '2', no_color)}")

    print()
    print(_paint("presets", "1", no_color))
    for name, preset in sorted(PRESETS.items()):
        names = ", ".join(t.name for t in preset.targets)
        print(f"  {name:10s} {names}")
        if preset.note:
            print(f"             {_paint(preset.note, '2', no_color)}")

    reported = [t.name for t in TARGETS.values() if t.confidence != "verified"]
    if reported:
        print()
        print(
            _paint(
                "warning: these paths are community-reported, not confirmed "
                f"against each agent's docs: {', '.join(sorted(reported))}",
                "33",
                no_color,
            )
        )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    no_color = args.no_color
    project_root = Path(args.path)
    source_root = project_root / args.source
    target_set = resolve(args.target)

    if not source_root.is_dir():
        print(f"skillport: source directory not found: {source_root}", file=sys.stderr)
        return 2

    report = check(project_root, source_root, target_set)

    if args.format == "json":
        payload = {
            "source": str(source_root),
            "skills": report.skills,
            "targets": [t.name for t in target_set.targets],
            "in_sync": len(report.in_sync),
            "missing": [
                {"target": s.target.name, "skill": s.skill_name, "path": str(s.destination)}
                for s in report.missing
            ],
            "drifted": [
                {"target": s.target.name, "skill": s.skill_name, "path": str(s.destination)}
                for s in report.drifted
            ],
            "extra": [
                {"target": s.target.name, "skill": s.skill_name, "path": str(s.destination)}
                for s in report.extra
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        red = lambda t: _paint(t, "31", no_color)  # noqa: E731
        yellow = lambda t: _paint(t, "33", no_color)  # noqa: E731
        green = lambda t: _paint(t, "32", no_color)  # noqa: E731
        dim = lambda t: _paint(t, "2", no_color)  # noqa: E731
        cyan = lambda t: _paint(t, "36", no_color)  # noqa: E731

        print(f"source: {source_root}  ({len(report.skills)} skills)")
        print(f"targets: {', '.join(t.name for t in target_set.targets)}")
        print()

        for state in report.in_sync:
            print(f"  {green('sync')}     {state.target.name:10s} {state.skill_name}")
        for state in report.missing:
            print(f"  {red('missing')}  {state.target.name:10s} {state.skill_name}")
        for state in report.drifted:
            print(f"  {yellow('drifted')}  {state.target.name:10s} {state.skill_name}")
            detail = report.differences.get((state.target.name, state.skill_name))
            if detail:
                only_source, only_target, changed = detail
                if changed:
                    print(f"             {dim('changed: ' + ', '.join(changed[:6]))}")
                if only_source:
                    print(f"             {dim('missing in target: ' + ', '.join(only_source[:6]))}")
                if only_target:
                    print(f"             {dim('only in target: ' + ', '.join(only_target[:6]))}")
        for state in report.extra:
            print(f"  {cyan('extra')}    {state.target.name:10s} {state.skill_name} {dim('(not in source)')}")

        print()
        if not report.has_problems:
            print(green("all targets in sync"))
        else:
            parts = []
            if report.missing:
                parts.append(red(f"{len(report.missing)} missing"))
            if report.drifted:
                parts.append(yellow(f"{len(report.drifted)} drifted"))
            if report.extra:
                parts.append(cyan(f"{len(report.extra)} extra"))
            print(" · ".join(parts) + dim("  → run `skillport sync`"))
            print(
                dim(
                    "note: counts are per target, so one skill out of sync in "
                    "three targets counts as three."
                )
            )

    return 1 if report.has_problems else 0


def cmd_sync(args: argparse.Namespace) -> int:
    project_root = Path(args.path)
    source_root = project_root / args.source
    target_set = resolve(args.target)

    if not source_root.is_dir():
        print(f"skillport: source directory not found: {source_root}", file=sys.stderr)
        return 2

    skills = discover_skills(source_root)
    if not skills:
        print(f"skillport: no SKILL.md found under {source_root}", file=sys.stderr)
        return 2

    if args.dry_run:
        targets = ", ".join(t.name for t in target_set.targets)
        print(f"would sync {len(skills)} skill(s) to: {targets}")
        for skill in skills:
            for target in target_set.targets:
                print(f"  {skill.name} -> {target.directory}/{skill.name}")
        return 0

    written = sync(project_root, source_root, target_set, only=args.skill)
    for path in written:
        try:
            shown = path.relative_to(project_root)
        except ValueError:
            shown = path
        print(f"  wrote {shown}")
    print(f"\n{len(written)} path(s) synced")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    project_root = Path(args.path)
    source_root = project_root / args.source
    target_set = resolve(args.target)

    if not source_root.is_dir():
        print(f"skillport: source directory not found: {source_root}", file=sys.stderr)
        return 2

    # Preview first: deleting is the one operation that loses work.
    from .sync import check as _check

    report = _check(project_root, source_root, target_set)
    if not report.extra:
        print("nothing to prune")
        return 0

    print("would remove:")
    for state in report.extra:
        print(f"  {state.destination}")

    if not args.yes:
        print(
            "\nthis deletes directories. re-run with --yes to proceed.",
            file=sys.stderr,
        )
        return 2

    removed = prune(project_root, source_root, target_set)
    print(f"\nremoved {len(removed)} director{'y' if len(removed) == 1 else 'ies'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillport",
        description="Keep Agent Skills in one place and sync them to every agent.",
    )
    parser.add_argument("--version", action="version", version=f"skillport {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("path", nargs="?", default=".", help="project root")
    common.add_argument(
        "--source", default="skills", help="source directory (default: skills)"
    )
    common.add_argument(
        "--target",
        action="append",
        metavar="NAME",
        help="target or preset, repeatable (default: common)",
    )
    common.add_argument("--no-color", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="show targets and presets")
    p_list.add_argument("--no-color", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_check = sub.add_parser("check", parents=[common], help="report drift")
    p_check.add_argument("--format", choices=("text", "json"), default="text")
    p_check.set_defaults(func=cmd_check)

    p_sync = sub.add_parser("sync", parents=[common], help="copy source to targets")
    p_sync.add_argument("--skill", action="append", help="sync only this skill")
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.set_defaults(func=cmd_sync)

    p_prune = sub.add_parser("prune", parents=[common], help="remove extra skills")
    p_prune.add_argument("--yes", action="store_true", help="confirm deletion")
    p_prune.set_defaults(func=cmd_prune)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())