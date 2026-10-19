# Judgment rubric and default classes

## How to answer
Answer every question for every skill, skills in alphabetical order, with exactly one of:
- **No**: nothing found.
- **Yes**: line number(s) and the exact words quoted (under 15 words) as evidence.
- **Unsure**: say what information is missing.

A Yes without a line number and quote counts as No. Report nothing outside this rubric except under "Other" (at most 3 per skill, each with line and quote). Finding IDs are `skill:RULE:Lline`, the same format the script prints.

Projected savings: a CANDIDATE CUT counts toward the floor only when its rubric question is Yes (BD-1 to J1, BD-2 to J2, BD-3 to J3, BD-4 to J4); BD-5 candidates are confirmed by reading. The ceiling is every candidate.

## Rubric
| Q | Rule | Question |
|---|---|---|
| J1 | BD-1 | Does a Purpose, Triggers, or When-to-use block restate the description? |
| J2 | BD-2 | Does an anti-pattern list repeat rules stated elsewhere in the skill? |
| J3 | BD-3 | Does a checklist repeat the rules instead of adding ordering or verification? |
| J4 | BD-4 | Is any template, table, or convention stated twice, in this skill or another? |
| J5 | BD-8 | Do two statements contradict each other? |
| J6 | BD-9 | Is an identifier used that the skill never defines? |
| J7 | BD-10 | Does the collect step omit something the template needs, or collect something unused? |
| J8 | BD-16 | Is there lore or flavor text that changes no behavior? |
| J9 | BD-14 | Is a block needed in under half of runs that could move to `references/` (NC-4)? |
| J10 | TS-1 | Is the trigger broader than the task it serves? |
| J11 | TS-2 | Does the body mandate reads, searches, or waits on every run? |
| J12 | TS-3 | Does another skill cover the same trigger? |
| J13 | TS-5 | Is the description missing keywords a user would type for this task? |
| J14 | XS-2 | Does each "Not for" sibling's description cover the redirected case? |
| J15 | DF-2 | Which blocks are fragile (exact commands, strict formats) and must not be trimmed? List line ranges. |

## Default class by rule
Give each finding the class below. Deviate only with a stated reason.

| Class | Rules |
|---|---|
| **Safe** (mechanical, behavior-preserving) | BD-1, BD-2, BD-3, BD-5, BD-6, BD-7 (suffix or path), BD-11, BD-16, BD-25, FM-8 |
| **Decision** (changes behavior, triggers, names, or cost) | every edit to a description (FM-3, FM-4, FM-5, FM-7, FM-9, FM-11, FM-13); renames (FM-2, FM-14); FM-1, FM-12; BD-4, BD-8, BD-10, BD-14, BD-19, BD-20, BD-21; all TS; XS-2, XS-4, XS-6; all NC |
| **Blocked** (needs information the auditor lacks) | BD-9, BD-7 (missing referenced file), XS-3 |
