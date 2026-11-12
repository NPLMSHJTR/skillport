---
name: example-review
description: Reviews a code change for the riskiest thing first. Use when the user asks for a review of a diff, a pull request, or a set of uncommitted changes.
license: MIT
---

# Example review

This is a reference skill shipped with skillport. It exists to demonstrate the
layout a skill should have, and to give `skillport sync` something real to move.
Replace it with your own.

## Steps

1. Get the change. If the user gave a range, use it:

   ```bash
   git diff <range>
   ```

   Otherwise use the working tree:

   ```bash
   git diff HEAD
   ```

2. Find the single riskiest change. Rank by what happens if it is wrong:
   data loss first, then silent wrong output, then availability, then style.

3. Report it first, with the file and line, and say what breaks.

4. Only then list the rest, in the same order.

## Rules

- One finding per paragraph. A finding is a claim about behaviour, not a
  preference.
- Quote the line. A finding without a line number cannot be checked.
- If nothing is risky, say so and stop. Manufacturing a finding to look thorough
  is worse than reporting nothing.
- Do not suggest a rewrite of a file you were not asked about.

## Reference

Severity ranking and the wording to use is in
[references/severity.md](references/severity.md).