# Compatibility

Where each agent reads skills from, what was actually verified, and how to check
your own installation.

The honesty rule for this file: a path is `verified` only if it was confirmed
against the agent's own documentation or a working installation. Everything else
is `reported`, meaning it is widely repeated in the community and I have not
confirmed it. `skillport list` marks the difference, because a tool that silently
writes to the wrong directory is worse than one that admits uncertainty.

## The table

| agent | directory | manifest | confidence | note |
| --- | --- | --- | --- | --- |
| Codex | `.codex/skills/` | none | **verified** | Project-level skills; the directory structure is confirmed in the Codex repository. |
| Claude Code | `.claude/skills/` | none | reported | Widely documented by users. Not confirmed against vendor docs here. |
| Cursor | `.cursor/skills/` | none | reported | Support varies by release; check your version before relying on it. |
| Gemini CLI | `.gemini/skills/` | none | reported | Reported by users; not confirmed. |
| Windsurf | `.windsurf/skills/` | none | reported | Reported by users; not confirmed. |
| OpenCode | `.opencode/skills/` | none | reported | Reported by users; not confirmed. |
| cross-agent | `.agents/skills/` | none | reported | Convention used by some marketplaces; not tied to one product. |

## Why so few are verified

Because verifying takes time and the ecosystem moves. The one path marked verified
was confirmed by reading the Codex repository, where skills live under
`.codex/skills/` and each is a directory with a `SKILL.md`. Everything else in the
table comes from documentation written by users rather than vendors.

That asymmetry is worth stating plainly rather than hiding behind a green table:
**most of this tool's target table is unconfirmed.** If you install it and one of
these is wrong, the tool will create a directory nobody reads.

## How to check your own installation

The reliable method, which does not depend on this document being current:

1. Install the agent and confirm it starts.
2. Create a skill in the candidate directory:

   ```
   <candidate>/
   └── probe-skill/
       └── SKILL.md
   ```

   with this content:

   ```markdown
   ---
   name: probe-skill
   description: Use when the user says the exact words "probe skill test".
   ---

   Reply with the single word: PROBE-OK
   ```

3. Start the agent in that project and say exactly: `probe skill test`.
4. If it replies `PROBE-OK`, the path is correct and the description matching
   works.

This takes two minutes and settles the question for your version, which is more
than any table can do. If it works, open an issue with your agent version and the
result — that is how a `reported` row becomes `verified`.

## What happens if a path is wrong

Nothing dangerous, but nothing useful either. `skillport sync` creates the
directory, writes the skill, and reports success. The agent scans somewhere else
and never sees it. There is no error, which is exactly why the confidence column
exists.

## Adding a target

Edit `src/skillport/targets.py`:

```python
TARGETS["newagent"] = Target(
    name="newagent",
    directory=".newagent/skills",
    confidence="reported",
    note="Where this came from and what remains unconfirmed.",
)
```

Add it to a preset if it belongs in the common set, add a test asserting the
directory is created, and update this file. The table is data; the tests are what
keep the data honest.

## A note on drift and manifests

Fingerprints exclude packaging files (`plugin.json`, `.codex-plugin`,
`manifest.json`, `skill.json`, `.app.json`). The reasoning: those files describe
packaging, and packaging legitimately differs per target.

The cost of that choice is real and worth knowing. If a future agent needs a
manifest whose content encodes part of the skill's behaviour — a version pin, a
tool allowlist — then changing that manifest will not register as drift. When that
day comes, the fix is to include the manifest in the fingerprint for targets that
declare one, which is a small change in `fingerprint.py` and a breaking change to
existing fingerprints.