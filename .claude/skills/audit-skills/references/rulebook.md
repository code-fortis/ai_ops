# Skill audit rulebook: frontmatter and body rules

## Contents
- Cost model
- Canonical skeleton
- Frontmatter rules (FM)
- Body rules (BD)

Rule IDs: FM = frontmatter, BD = body. Rules marked *(heuristic)* are judgment calls, not documented limits. Script flags carry these IDs. Cost accounting (NC), trigger scope (TS), cross-skill checks (XS) and trigger verification are in the review guide.

## Cost model

| Level | What loads | When | Cost profile |
|---|---|---|---|
| 1. Metadata | `name` + `description` of **every** installed skill | Every session | Paid always; the most expensive text per word |
| 2. Body | `SKILL.md` below the frontmatter | When the skill triggers | Paid per trigger; keep under ~500 lines |
| 3. Resources | `references/`, `assets/`, `scripts/` | Only when Claude opens or runs them | Paid on demand; scripts can run without being read |

Consequences:
- A word in the description costs more than a word in the body. A word in `references/` costs less than either.
- Words that **duplicate** each other cost twice. Words that **never change behavior** cost for nothing.
- A skill that **fails to trigger** costs more than any trimming saves, because Claude fumbles the task unaided. Never cut a real trigger keyword to save tokens.
- Skills load mainly for non-trivial tasks. A simple one-step request may not trigger a skill even with a perfect description.

Documented sizing: SKILL.md body under 500 lines (official best-practices page); about 5,000 tokens recommended (open Agent Skills spec). Reference files over 100 lines get a contents list, and references stay one level deep from SKILL.md, because Claude may read nested files only partially (for example with `head -100`). In claude.ai the `view` tool truncates the middle of files over 16,000 characters, so keep any file a session must read whole under that. No documented "first 200 lines only" cutoff for SKILL.md was found; do not design around one.

Token counts differ by client. Use `scripts/measure_skills.py` for relative comparison, not exact billing.

---

## Canonical skeleton

```
skill-name/
├── SKILL.md          required: frontmatter + instructions
├── references/       optional: docs read only when needed
├── assets/           optional: templates, icons, fonts used in output
└── scripts/          optional: deterministic or repetitive code
```

Body skeleton:

```markdown
---
name: skill-name
description: <Verb> <artifact> for <situation>. Use when <phrases users actually say>.
---

# skill-name

Output: `<path/pattern>`
Not for: <case> (`sibling-a`), <case> (`sibling-b`).

## Frontmatter rules (FM)

| ID | Rule | Check |
|---|---|---|
| FM-1 | Required: `name`, `description`. Other keys the validator allows: `license`, `allowed-tools`, `metadata`, `compatibility` (max 500 chars; only when a specific tool or dependency is truly required). Any other key fails validation. Add optional fields only when needed; never remove one the platform relies on. Put a version under `metadata` (`version: "1.0.0"`, quoted so it stays a string); a top-level `version:` key fails validation. | Script |
| FM-2 | `name`: lowercase letters, digits and single hyphens only (no leading, trailing or doubled hyphens), max 64 chars, equal to the folder name. Must not contain the reserved words "anthropic" or "claude" (official docs). | Script |
| FM-3 | Description formula: `<Verb> <artifact> for <situation>. Use when <trigger phrases>.` | Reads as two short sentences |
| FM-4 | Description contains the words a user would actually type (for example "design doc", "RFC", "incident"). Keywords hidden only in the body (`**Triggers**:` lines) do nothing, because the body loads after the decision to trigger. | Every body trigger keyword also appears in the description |
| FM-5 | Add a **discriminator** against sibling skills (*existing* vs *proposed*, *resolved* vs *open*, *retrospective* vs *forward*). | Description alone separates it from each sibling; count the words added (NC-2) |
| FM-6 | Be "pushy" about triggering, not long. Prefer a keyword list over prose. | Words per description |
| FM-7 | Exclude from description: workflow steps, file paths, section lists, history, markdown formatting. | None present |
| FM-8 | YAML safety: the frontmatter must parse. Quote a value containing `: ` or starting with a special character. Use LF line endings (the validator's frontmatter pattern expects `\n`). | Script |
| FM-9 | Length: target **25-60 words** *(heuristic)*. Flag **>100** (the guide's approximate ceiling). Hard validator limit: **1024 characters**. Anthropic's own shipped skills run 70-160 words, so the target is an aim for project skills, never a reason to drop trigger terms. | `descW` column |
| FM-10 | No two skills may share the same primary trigger phrases. If they do, add a discriminator (FM-5) or merge them. | Collision check (XS-4) |
| FM-11 | **No angle brackets (`<` or `>`) in the description**; the validator rejects them and packaging fails. Common culprit: path templates such as `PLAN_<scope>_<slug>.md` (also an FM-7 violation). | Script |
| FM-12 | **Exactly one `SKILL.md` per skill**, at `<folder>/SKILL.md`. Nested ones are rejected on upload (Skills API, claude.ai); only Claude Code's filesystem loads them. Name supporting docs anything else, e.g. `references/topic.md`. | Script |
| FM-13 | **Write the description in third person** ("Extracts text from PDFs" or "Extract text from PDFs"), never "I can ..." or "You can ...". It is injected into the system prompt, and mixed point of view can hurt discovery. | Script (check) |
| FM-14 | **One naming pattern across the collection.** Docs favor gerunds (`processing-pdfs`); verb-noun (`process-pdfs`) and noun phrases (`pdf-processing`) are acceptable. Avoid vague names (`helper`, `utils`, `tools`, `documents`). | Script + judgment |

---

## Body rules (BD)

| ID | Rule | Typical fix |
|---|---|---|
| BD-1 | **No restating the description.** Delete `Purpose`, `Triggers` and `When to use` blocks that repeat it. Keep `Output:` (it is an instruction) and `Not for:` (it is routing). | Delete; fold unique content into the description |
| BD-2 | **Anti-pattern lists that repeat rules are deleted.** Fold each one into the rule it violates; keep only genuinely unique guardrails (see BD-19). | Merge into Rules |
| BD-3 | **Checklists that repeat rules are deleted.** Keep only non-obvious ordering ("write the summary last"). Verification moves to a "Done when" list (BD-20), not a second checklist. | Shrink to "Order of work" |
| BD-4 | **One source of truth per fact.** A template, status lifecycle or naming convention lives in exactly one place. Others point to it. If a template is short and needed every run, inline it. If it is large or shared, put it in one file and point to it. | Dedupe; pointer |
| BD-5 | **No changelog in skill bodies**: rename dates, deleted-skill notes, "History" blocks, "Renamed on..." footers. These belong in git. Also remove time-sensitive statements ("before August 2025 use X"): state the current method, and put legacy behavior in a clearly labelled "old patterns" note if it must stay. | Delete |
| BD-6 | **No unresolved placeholders** ("your project's docs convention"). Claude cannot resolve them. Insert the real path or delete the line. | Fill or delete |
| BD-7 | **Consistent references.** Skill names without `.md`. One path prefix style (`.claude/references/...` vs `references/...`). Every referenced file, skill and tool exists. | Normalize; verify |
| BD-8 | **No contradictions.** Example: a template offers `Status: Open` while rules say "record resolved items only". | Pick one; if intent is unclear, ask |
| BD-9 | **Every identifier is defined** (for example `ND-NNN`, `F-50`). Say how to derive it, or drop it. | Define or delete |
| BD-10 | **Inputs match the template.** Everything the template needs must be in the "collect" step. | Add missing, remove unused |
| BD-11 | **Templates use clean fences.** Do not escape backticks with backslashes. Use a longer outer fence (four backticks) around a template that contains triple-backtick blocks. | Fix fences |
| BD-12 | **Imperative voice, reasons over shouting.** Explain *why* instead of stacking MUST/NEVER. Keep ALL-CAPS only for a true format lock. | Rewrite |
| BD-13 | **Tool names are portable.** Prefer "ask the user" over a client-specific tool name unless the skill is deliberately tied to that client. | Reword |
| BD-14 | **Content only needed sometimes goes to `references/`.** Include "read X when Y" in the body. Give any reference over 100 lines a contents list at the top, and keep references one level deep from SKILL.md (a reference that points to another reference may be read only partially). Organize multi-variant skills as `SKILL.md` (workflow plus selection) and one reference file per variant. | Extract, only if not needed every run (NC-4) |
| BD-15 | **Deterministic, repeated work becomes a script**, not prose steps. | Extract to `scripts/` |
| BD-16 | **No lore or flavor** ("rumored to be 6 pages", internal URL schemes) unless it changes behavior. | Delete |
| BD-17 | **Stay general.** Prefer the principle over a narrow worked example. If you keep examples, keep two, not five. | Cut |
| BD-18 | **Output formats are explicit** when format matters (exact template or filename pattern). | Add |
| BD-19 | **"Never" section: optional, unique guardrails only.** Keep a prohibition if it blocks something Claude would plausibly do by default (implementing before approval, re-embedding a template, renaming a skill). Delete any that merely negate a rule already stated. Give each a one-clause reason. Replaces anti-pattern lists; never append (NC-3). | Keep, trim, or delete |
| BD-20 | **"Done when" section: optional, for skills that produce an artifact or have side effects** (files written, indexes updated, rules appended). 3-6 items, each checkable by inspection. It **replaces** the execution checklist and self-check; never keep both. Skip it when finishing the steps is the done state. Replaces checklists; never append (NC-3). | Add or consolidate |
| BD-21 | **Task-list protocol: one line, only on multi-step skills with side effects.** Wording: "If a task-list tool is available, create one item per Done-when bullet and tick them off; otherwise continue without comment." Rules: name the tool generically (BD-13); items come from "Done when", never a third list; never mention the tool's absence; a tool error never blocks the task. Put the project-wide default once in `CLAUDE.md`; repeat it in a skill only when the items are skill-specific. Skip it for single-artifact skills. It adds a line plus tool calls on every run (NC-3). | Add, or remove duplicates |
| BD-22 | **One term per concept** throughout a skill (not "endpoint", "URL", "route", "path" interchangeably). | Normalize |
| BD-23 | **Give a default with an escape hatch**, not a menu of equal options ("use pdfplumber; for scanned PDFs use OCR instead"). | Rewrite |
| BD-24 | **MCP tools use fully qualified names** (`ServerName:tool_name`) to avoid "tool not found" errors. | Qualify |
| BD-25 | **Forward slashes in all paths** (`scripts/helper.py`); backslashes fail on Unix. | Script |

### Safety (non-negotiable)
- No malware, exploit code, or content that compromises security.
- A skill's contents must not surprise the user relative to its description. Flag any skill that does something its description doesn't say (data exfiltration, hidden network calls, silent deletions).
- No secrets, tokens, internal hostnames or personal data in skill files. Flag, do not copy into the report.

---

