"""Content fingerprints, so drift can be judged without comparing bytes.

Why not compare file trees directly? Because the copies are not meant to be
byte-identical. A target may add a manifest, rewrite a path in prose, or normalise
line endings, and still be correctly synced. Comparing bytes would report drift on
every such file forever, and a check that always fails is a check people delete.

Instead, each skill gets a fingerprint over its *semantic* content:

    - the set of relative file paths, sorted
    - each file's text with line endings normalised and trailing whitespace
      stripped from line ends
    - file mode is ignored, because it is not content

Two skills with the same fingerprint are in sync for the purpose of the tool,
even if their manifests differ. Two skills with different fingerprints are not,
and the differing paths are reported so the fix is obvious.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

# Directories inside a skill that carry content an agent reads.
CONTENT_DIRS = {"", "scripts", "references", "assets"}

# Files that describe the packaging rather than the instruction. Their content
# legitimately differs per target, so they are excluded from the fingerprint.
MANIFEST_NAMES = {
    ".codex-plugin",
    "plugin.json",
    "manifest.json",
    "skill.json",
    ".app.json",
}

TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".py", ".js", ".ts", ".sh", ".bash",
    ".json", ".yaml", ".yml", ".toml", ".sql", ".ps1", ".rb", ".go", ".rs",
}


@dataclass
class Fingerprint:
    """A skill's content identity plus the per-file hashes behind it."""

    digest: str
    files: dict[str, str] = field(default_factory=dict)

    def differing_paths(self, other: "Fingerprint") -> tuple[list[str], list[str], list[str]]:
        """Return (only_in_self, only_in_other, changed), all sorted."""
        mine = set(self.files)
        theirs = set(other.files)
        only_self = sorted(mine - theirs)
        only_other = sorted(theirs - mine)
        changed = sorted(
            path for path in mine & theirs if self.files[path] != other.files[path]
        )
        return only_self, only_other, changed


def _normalise_text(text: str) -> str:
    """Normalise line endings and strip trailing whitespace from each line."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip("\n")


def _file_hash(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return "unreadable"

    if path.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return hashlib.sha256(_normalise_text(text).encode("utf-8")).hexdigest()

    return hashlib.sha256(raw).hexdigest()


def _is_excluded(relative: Path) -> bool:
    """Packaging artefacts and noise are not content."""
    parts = relative.parts
    if any(part.startswith(".") and part not in (".",) for part in parts):
        return True
    if any(part in ("__pycache__", "node_modules", ".venv") for part in parts):
        return True
    if relative.name in MANIFEST_NAMES:
        return True
    if relative.name.endswith((".pyc", ".pyo")):
        return True
    return False


def fingerprint(skill_dir: Path) -> Fingerprint:
    """Compute the fingerprint of one skill directory."""
    if not skill_dir.is_dir():
        return Fingerprint(digest="missing")

    files: dict[str, str] = {}
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir)
        if _is_excluded(relative):
            continue
        files[str(relative).replace("\\", "/")] = _file_hash(path)

    payload = json.dumps(files, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return Fingerprint(digest=digest, files=files)