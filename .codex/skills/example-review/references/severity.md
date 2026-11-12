# Severity ranking

The order to report findings in, and why that order and not another.

## The ranking

| rank | category | what it means | example |
| --- | --- | --- | --- |
| 1 | data loss | existing data is destroyed or made unreadable | a migration that drops a column still being read |
| 2 | silent wrong output | the code returns a wrong answer without erroring | an off-by-one that excludes the last row |
| 3 | availability | the service stops serving under load | an unbounded query in a hot path |
| 4 | unsafe default | correct only if the caller remembers something | a function that opens a file for write by default |
| 5 | maintainability | the code will be wrong after the next change | duplicated logic in two files that must stay equal |
| 6 | style | a convention is not followed | inconsistent naming |

## Why this order

Because it is the order of cost when the change is wrong.

Ranks 1 and 2 are permanent: data that is gone is gone, and output that is wrong
without an error may be acted on for months. Rank 3 is temporary but visible.
Ranks 4 and 5 cost someone later rather than now. Rank 6 costs nothing that can
be measured.

The distinction that matters most is between 2 and 3. A service that returns 500
is annoying and gets fixed. A service that returns the wrong number quietly is
the reason people stop trusting a system. Rank 2 above rank 3 reflects that.

## Wording

Use the structure "if X, then Y, because Z", with the line quoted. For example:

> `src/parse.py:42` reads `row[3]` but the header has three columns. If a row has
> only three fields, this raises `IndexError` and the whole batch fails, because
> there is no per-row error handling in the loop below.

Compare with:

> The parsing logic could be cleaner.

The second sentence cannot be checked, agreed with, or acted on. It is not a
finding; it is a mood.

## What not to report

- Anything you cannot point at a line for.
- Style preferences when a linter already runs; the linter is more consistent
  than you.
- Suggestions that require rewriting code outside the diff. Note them separately
  if they matter, and only after the findings above.
- The same issue twice. If a bug appears in three places, report it once and say
  it repeats in the other two, with lines.

## When to report nothing

When the change is fine. This happens often and it is the correct outcome. A
reviewer who always finds something trains the author to ignore reviews.