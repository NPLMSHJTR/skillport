"""Where each agent expects to find skills, and how it wants them shaped.

Everything here is data, not logic, because the facts change faster than the code
does. When an agent moves its directory or adds a manifest field, this table is
the only thing that has to be edited.

A word on honesty: each target carries a `confidence` field. `verified` means the
path was checked against that agent's own documentation or a working installation.
`reported` means the path is widely repeated in the community but I have not
confirmed it myself. skillport prints a warning for `reported` targets, because a
tool that silently guesses where to write files is worse than one that says it is
guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Target:
    """One agent's skill location and conventions."""

    name: str
    # Directory, relative to the repository root, that the agent scans.
    directory: str
    # Whether the agent reads a per-skill manifest in addition to SKILL.md.
    manifest: str | None = None
    # Whether nested directories other than scripts/references/assets are allowed.
    flat: bool = True
    confidence: str = "reported"
    note: str = ""


@dataclass(frozen=True)
class TargetSet:
    name: str
    targets: tuple[Target, ...]
    note: str = ""


# --- The table --------------------------------------------------------------

TARGETS: dict[str, Target] = {
    "codex": Target(
        name="codex",
        directory=".codex/skills",
        confidence="verified",
        note="Project-level skills live under .codex/skills/.",
    ),
    "claude": Target(
        name="claude",
        directory=".claude/skills",
        confidence="reported",
        note="Claude Code project skills; confirm against your version.",
    ),
    "cursor": Target(
        name="cursor",
        directory=".cursor/skills",
        confidence="reported",
        note="Cursor's skill directory; support varies by release.",
    ),
    "agents": Target(
        name="agents",
        directory=".agents/skills",
        confidence="reported",
        note="Cross-agent convention used by some marketplaces.",
    ),
    "gemini": Target(
        name="gemini",
        directory=".gemini/skills",
        confidence="reported",
        note="Gemini CLI skill directory.",
    ),
    "windsurf": Target(
        name="windsurf",
        directory=".windsurf/skills",
        confidence="reported",
        note="Windsurf skill directory.",
    ),
    "opencode": Target(
        name="opencode",
        directory=".opencode/skills",
        confidence="reported",
        note="OpenCode skill directory.",
    ),
}


PRESETS: dict[str, TargetSet] = {
    "codex": TargetSet("codex", (TARGETS["codex"],)),
    "claude": TargetSet("claude", (TARGETS["claude"],)),
    # The set most people actually want: the two ecosystems with real skill
    # support today, plus the neutral one that marketplaces read.
    "common": TargetSet(
        "common",
        (TARGETS["codex"], TARGETS["claude"], TARGETS["agents"]),
        note="The three directories most skill tooling looks in.",
    ),
    "all": TargetSet("all", tuple(TARGETS.values())),
}


def resolve(names: list[str] | None) -> TargetSet:
    """Turn a list of target names into a TargetSet.

    Accepts preset names (`common`, `all`) and individual target names, mixed.
    """
    if not names:
        return PRESETS["common"]

    chosen: list[Target] = []
    seen: set[str] = set()
    for name in names:
        key = name.strip().lower()
        if key in PRESETS:
            for target in PRESETS[key].targets:
                if target.name not in seen:
                    chosen.append(target)
                    seen.add(target.name)
            continue
        if key in TARGETS:
            if key not in seen:
                chosen.append(TARGETS[key])
                seen.add(key)
            continue
        raise ValueError(
            f"unknown target `{name}`; known targets: "
            + ", ".join(sorted(TARGETS))
            + "; presets: "
            + ", ".join(sorted(PRESETS))
        )

    return TargetSet("custom", tuple(chosen))