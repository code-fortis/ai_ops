# Skill audit review guide: cost, trigger and cross-skill checks

## Contents
- Net-cost accounting (NC)
- Protect, then trim (DF)
- Trigger scope and cost risk (TS)
- Cross-skill rules (XS)
- Trigger verification
- Calibration example

Rules here need judgment, so findings from them are usually Decisions. Lint rules (FM, BD) are in the rulebook.

## Net-cost accounting (NC)

Goal: fewer tokens overall. Two meters per skill: always-on metadata (paid every session) and per-trigger body (paid each time the skill loads, plus any reference reads). `scripts/measure_skills.py --baseline` reports both.

| ID | Rule |
|---|---|
| NC-1 | **Two meters.** Cost every change on metadata and on body. A metadata word costs the most because every session pays it. |
| NC-2 | **No-regression gate.** After fixes, no skill's metadata or body tokens may exceed its baseline unless the finding is an approved Decision that states "adds ~N tokens" and the benefit (a trigger that was missing, a defect fixed, information Claude lacked). Revert or justify every REGRESSION line. |
| NC-3 | **Replace, never append.** These recommendations add text, so apply them only by replacing duplicated text: "Never" (BD-19) replaces anti-pattern lists; "Done when" (BD-20) replaces checklists and self-checks; description keywords and discriminators (FM-4, FM-5) replace filler words. The task-list line (BD-21) adds a line and tool calls on every run; use it only where side effects justify it. |
| NC-4 | **Move content to `references/` only if it is not needed every run** *(heuristic: needed in under half of runs)*. Always-needed content moved out costs a pointer plus a file read every run. |
| NC-5 | **Prefer a reference file over a new skill.** Each skill adds about 70 tokens to every session. Merge duplicate skills; split a large skill into references, not into more skills. |
| NC-6 | **Trigger direction is a cost.** Broader triggers load bodies more often; narrower ones less often. State the direction in every trigger finding and make it a Decision. Do not make a description pushier without a failing should-trigger test. |
| NC-7 | **A missed trigger is a false saving.** Run the trigger tests before and after. A skill that stops loading is broken, not cheaper. |
| NC-8 | **Snapshot first.** Copy the skills directory before editing. After fixes run the script with `--baseline <snapshot>` and put its table in the report. State in "Not audited / assumptions" what it cannot measure: trigger frequency, extra file reads, task-list tool calls. |

## Protect, then trim (DF)

| ID | Rule |
|---|---|
| DF-1 | **Concision test (official).** For each block ask: does Claude really need this? Can Claude be assumed to know it? Does it justify its tokens? Cut what fails; keep what Claude cannot infer (project paths, conventions, formats, gotchas). |
| DF-2 | **Protect fragile steps.** Where an operation is fragile or consistency-critical (exact commands, required sequences, strict output formats), low freedom is correct. Never trim or paraphrase those; mark them protected in the report and trim explanatory prose instead. |
| DF-3 | **Unused bundled files.** If evidence shows a reference file is never opened, it may be unnecessary or poorly signaled in SKILL.md. Raise it as a Question; do not delete. |

## Trigger scope and cost risk (TS): decisions, not auto-fixes

For each skill, answer these in the report. They affect behavior, so the user decides.

| ID | Question | Why it matters |
|---|---|---|
| TS-1 | Is the trigger **broader** than needed? (for example "3+ steps or >30 min" matches a lot of ordinary work.) | Every false trigger loads the whole body |
| TS-2 | Does the body mandate **expensive reads or actions on every run** (read multiple docs, wait for approval, run searches)? Could they be conditional? | Per-trigger cost multiplies |
| TS-3 | Does the skill **duplicate another** (leftover from a rename or merge)? | Two skills competing for one trigger |
| TS-4 | Are there **gates in other skills** that overlap (two different thresholds for "needs a plan")? State the interaction in two sentences, or unify. | Contradictory behavior |
| TS-5 | Could the skill be **undertriggering**? (missing keywords, vague description) | Failure costs more than bloat |

---

## Cross-skill rules (XS)

| ID | Rule |
|---|---|
| XS-1 | Build an **inventory table**: name, folder, description words, body lines, siblings referenced. |
| XS-2 | **Routing is symmetric.** If A says "not for X, use B", then B's description must plausibly cover X. |
| XS-3 | **Every referenced skill, file, template and command resolves** to something that exists. Report dangling references. |
| XS-4 | **Collision check.** List the 3-5 key trigger phrases of each skill. Any phrase appearing in two skills' descriptions is a collision. |
| XS-5 | **Metadata budget.** Report total always-on tokens (script output). Skills with the largest metadata-to-usefulness ratio are trimmed first. |
| XS-6 | **Dead or duplicate skills** are listed for deletion. The user approves each deletion. |
| XS-7 | **Shared content** (diagram conventions, commit-message format, ADR template) is stored once and referenced, if it appears in 3 or more skills. If it is one line, repeating it is cheaper than a pointer. |
| XS-8 | **Naming family consistency** (for example the `write-*` family): same description formula, same skeleton, same placement of `Output:` and `Not for:`. |

---

## Trigger verification

For each changed skill, write **3 should-trigger** and **3 should-not-trigger** prompts.
- Prompts must be **substantive and realistic**, the kind a real user types. Trivial one-step prompts will not trigger skills regardless of the description.
- At least one should-not prompt must be a **near miss that belongs to a sibling skill**.
- Run each with the skill installed. Record which skill, if any, loaded.
- Changed a description and a should-trigger now fails? Restore the dropped keywords.
- Test on every model the skill will run on (official guidance: a smaller model may need more detail, a larger one less), with at least three scenarios per skill.
- If your environment has the skill-creator description optimizer (it requires the `claude` CLI), use it after the manual pass. Otherwise manual testing is enough.

Save prompts as `evals/evals.json` inside the skill folder when you want them reusable:

```json
{
  "skill_name": "example-skill",
  "evals": [
    { "id": 1, "prompt": "realistic user request", "expected_output": "what should happen", "files": [] }
  ]
}
```

---

## Calibration example

Bloated (about 60 words):
`description: This skill should be used when the user wants to work with PDF documents. It can read text, extract tables, combine multiple PDFs into one file, split a PDF apart, rotate pages, add watermarks, create new PDFs, fill out forms, encrypt or decrypt files, and perform OCR on scanned documents.`

Lean (about 20 words), same triggers:
`description: Read, create, merge, split, fill, watermark, encrypt, or OCR PDFs. Use for any .pdf file or PDF request.`

The operation list moves to the body, which only loads when the skill triggers.

