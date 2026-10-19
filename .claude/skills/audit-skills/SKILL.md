---
name: "audit-skills"
description: Audit and fix a project's skills (SKILL.md files) for token bloat, weak triggers, duplication, overlapping skills, and broken references. Use when the user asks to audit, lint, review, trim, or clean up skills, or when skill descriptions are bloated, overlapping, or not triggering.
metadata:
  version: "1.3.0"
---

# audit-skills

Output: an audit report first; fixes only after the user approves it.
Not for: writing a new skill from scratch or running evals (`skill-creator`, if installed).

## Rules
- **Report first, edit second.** Fixes change files other sessions rely on, so the user approves before anything is touched.
- **Preserve behavior.** Trimming words, moving content to `references/`, and fixing contradictions are safe. Changing triggers, mandatory reads, gates, output paths, or status values is a decision for the user: list it, don't apply it.
- **Never cut a real trigger keyword to save tokens.** A skill that fails to trigger costs more than the trimming saves.
- **No skill may cost more after the fix.** Unless an approved Decision states the added tokens and the benefit, metadata and body must not grow. Replace text; don't append.
- **Be reproducible.** Mechanical findings are the script's FLAGS, copied verbatim with their IDs. Judgment findings come only from the rubric, each with a line number and a quote; no evidence, no finding. The same input must produce the same finding IDs.
- **Never rename or delete a skill unprompted.** Other skills and docs reference it.
- **Don't guess intent.** An undefined identifier or ambiguous convention goes under Questions.
- **Read before judging.** Audit only skills you have read in full, plus the files they reference.
- **Edit a copy if the skills directory is read-only**, and hand back the changed files.
- **Keep secrets out of the report.** Flag where they are, not what they say.

## Inputs to confirm
Skills root and scope (all skills or named ones). If the root is unclear, search for folders containing `SKILL.md` and ask which to audit. Reports are saved under `/tmp/skill-audit/` unless the user names another folder (use the environment's outputs folder if `/tmp` isn't visible to the user).

## Order of work
1. Snapshot the skills directory (`cp -r <skills-root> <snapshot>`), then run `python measure_skills.py <skills-root> --save` from this skill's `scripts/` folder. It prints sizes, an always-on token estimate, FLAGS with stable IDs, candidate cuts, shared trigger phrases, and an input fingerprint; saves that output under `/tmp/skill-audit/`; and prints a REPORT STEM path on stderr.
2. Read every file in the script's INPUT FINGERPRINT list, skills in alphabetical order; note references that don't exist.
3. Read `references/rulebook.md`, `references/review-guide.md`, and `references/rubric.md`. Answer every rubric question for every skill. Treat flags marked (check) as leads: confirm each by reading its line, then keep or drop it with a reason.
4. Give each finding the class from the rubric's default-class table; deviate only with a stated reason.
5. Write the report below to `<REPORT STEM>.md`, run `python render_report.py <REPORT STEM>.md` (same `scripts/` folder) for the HTML copy, then stop for approval. In chat give only the two file paths, the Summary and Projected savings lines, and the Decisions-needed list; print the full report only if asked.
6. After approval, apply approved items only, one skill per commit. Re-run the script with `--baseline <snapshot>`; revert or justify every REGRESSION line.
7. Verify triggers for each changed description (review-guide: Trigger verification).

## Report format
```
# Skill Audit Report - <date>
Fingerprint: ALL <hash from the script> | skills N, alphabetical
Summary: always-on ~X tokens | S safe, D decisions, B blocked
Projected savings: per skill, floor (rubric-confirmed CANDIDATE CUTS) and ceiling (all candidates), ~tokens per load; description savings only once an approved edit is measured
Mechanical findings: the script's FLAGS verbatim, each with its class and a keep/drop note for (check) items
Rubric answers: per skill, J1-J15 as No | Yes (line + quote) | Unsure (what is missing)
Decisions needed: finding ID, options, recommendation
Questions: finding ID, what you could not determine
Not audited / assumptions (the script cannot measure trigger frequency, extra reads, or task-list calls)
```
Projected savings come only from the script's CANDIDATE CUTS; actual savings are measured after the fixes with `--baseline`. To convert per-load savings into usage, multiply by trigger counts the user supplies, never guessed ones.

## Done when
- The report exists as .md and .html in the report folder, and chat holds only the summary and paths
- The report carries the input fingerprint, and every rubric question is answered for every skill, and projected savings are stated as a floor and a ceiling
- Every finding has an ID and a class; decisions and questions are listed separately
- Baseline comparison shows no unapproved increase in any skill's metadata or body
- After approval: one commit per skill, trigger tests recorded, no behavior change beyond approved decisions

If a task-list tool is available, create one item per Done-when bullet and tick them off; otherwise continue without comment.
