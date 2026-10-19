#!/usr/bin/env python3
"""Measure skill size, run deterministic lint checks, and compare against a baseline.

Usage:
  python measure_skills.py <skills-root>
  python measure_skills.py <skills-root> --baseline <snapshot-dir>
  python measure_skills.py <skills-root> --save            (saves output under /tmp/skill-audit)
  python measure_skills.py <skills-root> --save-dir <dir>  (saves output under <dir>)

Output is deterministic: the same input always prints the same text. It contains
  - per-skill sizes (metadata = always-on cost, body = on-trigger cost)
  - FLAGS: lint findings with stable IDs (skill:RULE:Lline) and rule IDs from references/rulebook.md
  - SHARED DESCRIPTION PHRASES: possible trigger collisions
  - CANDIDATE CUTS: sections/fields that usually duplicate other text, with exact token counts
    (upper bounds; the basis for projected savings)
  - INPUT FINGERPRINT: per-file hashes of every audited file, so two reports can be checked
    against identical input
  - with --baseline: per-skill token deltas against a pre-edit snapshot (REGRESSION = increase)
With --save the printed text is also written to <dir>/measure-<time>-<hash>.txt; the file holds
exactly the printed text, and the path plus a REPORT STEM for the report files go to stderr.
Token figures are chars/4, a rough estimate of static text only. Flags marked (check) are
heuristics: confirm by reading the line.
"""
import collections
import datetime
import hashlib
import io
import os
import pathlib
import re
import sys
import tempfile

try:
    import yaml
except ImportError:  # lint still runs, minus strict YAML parsing
    yaml = None

ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
RESERVED = ("anthropic", "claude")          # reserved words in names (official docs)
TOC_LINES = 100                             # reference files longer than this need a contents list
VIEW_CHARS = 16000                          # the claude.ai view tool truncates the middle above this
BODY_TOKENS = 5000                          # recommended body ceiling (open Agent Skills spec)
RANK = {"FM": 0, "BD": 1, "TS": 2, "XS": 3, "NC": 4, "DF": 5}
STOP = set("""a an and or the to of for in on with when use used using this that is are be it
as by from at not any if user users file files you your skill skills task tasks""".split())


HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FIELD = re.compile(r"^\*\*(purpose|triggers?)\*\*\s*:", re.I)
CUT_HEADINGS = (("purpose", "BD-1"), ("trigger", "BD-1"), ("when to use", "BD-1"),
                ("anti-pattern", "BD-2"), ("anti pattern", "BD-2"), ("antipattern", "BD-2"),
                ("execution checklist", "BD-3"), ("checklist", "BD-3"),
                ("see also", "BD-4"), ("history", "BD-5"), ("changelog", "BD-5"))


def find_cuts(folder, body, first_line):
    """Sections and fields that usually duplicate the description or other rules.
    Returns (folder, start_line, end_line, rule, label, tokens): upper bounds, not findings."""
    lines = body.split("\n")
    in_fence, heads, fields = False, [], []
    for i, text in enumerate(lines):
        if text.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        mm = HEAD.match(text)
        if mm:
            heads.append((i, len(mm.group(1)), mm.group(2)))
        elif FIELD.match(text):
            fields.append(i)
    spans = []
    for k, (i, level, title) in enumerate(heads):
        norm = re.sub(r"[^a-z0-9\- ]+", "", title.lower()).strip()
        rule = next((r for pre, r in CUT_HEADINGS if norm.startswith(pre)), None)
        if rule:
            j = next((h[0] for h in heads[k + 1:] if h[1] <= level), len(lines))
            spans.append((i, j - 1, rule, f'"{title}" section'))
    for i in fields:
        j = i
        while j + 1 < len(lines) and lines[j + 1].strip():
            j += 1
        spans.append((i, j, "BD-1", lines[i].split(":")[0].strip("*") + " field"))
    out, last_end = [], -1
    for start, end, rule, label in sorted(spans):
        if start <= last_end:  # inside an earlier candidate
            continue
        tok = len("\n".join(lines[start:end + 1])) // 4
        if tok >= 10:
            out.append((folder, first_line + start, first_line + end, rule, label, tok))
        last_end = end
    return out


def scan(root):
    root = pathlib.Path(root)
    paths = sorted(p for p in root.rglob("SKILL.md")
                   if not {"node_modules", "__pycache__"} & set(p.parts))
    names_by_dir = {p.parent: p.parent.name for p in paths}
    all_names = set(names_by_dir.values())
    prefix_count = collections.Counter(n.split("-")[0] for n in all_names if "-" in n)
    rows, flags, desc_tokens, files, cands = [], [], {}, [], []

    def flag(skill, rule, msg, line=None, loc=None):
        flags.append((skill, rule, line, loc, msg))

    for p in paths:
        folder = p.parent.name
        raw_bytes = p.read_bytes()
        raw = raw_bytes.decode("utf-8", errors="replace")
        files.append((folder, "SKILL.md", raw.count("\n") + 1, hashlib.sha256(raw_bytes).hexdigest()[:12]))

        def ln(pos):
            return raw.count("\n", 0, pos) + 1 if pos >= 0 else None

        if "\r\n" in raw:
            flag(folder, "FM-8", "CRLF line endings; the validator's frontmatter pattern expects LF")
        m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n?(.*)", raw, re.S)
        if not m:
            flag(folder, "FM-1", "no YAML frontmatter")
            continue
        fm_text, body = m.groups()
        boff = m.start(2)

        def bln(idx):
            return ln(boff + idx)

        fm = {}
        if yaml:
            try:
                fm = yaml.safe_load(fm_text)
                if not isinstance(fm, dict):
                    flag(folder, "FM-8", "frontmatter is not a YAML mapping")
                    fm = {}
            except yaml.YAMLError as e:
                flag(folder, "FM-8", f"invalid YAML (quote values containing ': '): {str(e).splitlines()[0]}")
        else:
            for k in ("name", "description"):
                mm = re.search(rf"^{k}:\s*(.*?)(?=^\S+:|\Z)", fm_text, re.M | re.S)
                if mm:
                    fm[k] = " ".join(mm.group(1).split())

        name = str(fm.get("name", "") or "").strip()
        desc = " ".join(str(fm.get("description", "") or "").split())
        name_line, desc_line = ln(raw.find("name:")), ln(raw.find("description:"))
        bad_keys = sorted(set(fm) - ALLOWED)
        if bad_keys:
            flag(folder, "FM-1", f"unexpected frontmatter keys: {', '.join(bad_keys)}", ln(raw.find(bad_keys[0] + ":")))
        if not name:
            flag(folder, "FM-1", "missing name")
        if not desc:
            flag(folder, "FM-1", "missing description")
        if name:
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
                flag(folder, "FM-2", f"name '{name}' must be lowercase kebab-case, no leading/trailing/double hyphens", name_line)
            if len(name) > 64:
                flag(folder, "FM-2", f"name is {len(name)} chars (max 64)", name_line)
            if name != folder:
                flag(folder, "FM-2", f"name '{name}' != folder '{folder}'", name_line)
            for word in RESERVED:
                if word in name:
                    flag(folder, "FM-2", f"name contains reserved word '{word}' (official docs)", name_line)
            if re.fullmatch(r"(helper|utils?|tools?|documents?|data|files?)", name):
                flag(folder, "FM-14", "vague name; say what the skill does", name_line)
        dw = len(desc.split())
        if dw > 100:
            flag(folder, "FM-9", f"description is {dw} words (guide ceiling ~100)", desc_line)
        if len(desc) > 1024:
            flag(folder, "FM-9", f"description is {len(desc)} chars (max 1024)", desc_line)
        if "<" in desc or ">" in desc:
            flag(folder, "FM-11", "angle brackets in description (rejected as XML tags)", desc_line)
        if re.search(r"(?i)\b(i can|i will|i'll|you can|you will|your|my)\b", desc):
            flag(folder, "FM-13", "first/second person in description; write in third person (check)", desc_line)
        if desc and not re.search(r"(?i)\buse\b|\btrigger", desc):
            flag(folder, "FM-3", "description has no 'Use when ...' trigger clause", desc_line)
        if re.search(r"[\w.-]+/[\w.<>_-]+", desc):
            flag(folder, "FM-7", "path-like text in description (check)", desc_line)
        if len(str(fm.get("compatibility", "") or "")) > 500:
            flag(folder, "FM-1", "compatibility over 500 chars", ln(raw.find("compatibility:")))

        blines = body.count("\n") + 1
        cands.extend(find_cuts(folder, body, ln(boff)))
        btok = len(body) // 4
        if blines > 500:
            flag(folder, "BD-14", f"body is {blines} lines (limit ~500): split into references/")
        if btok > BODY_TOKENS:
            flag(folder, "BD-14", f"body is ~{btok} tokens (recommended < {BODY_TOKENS})")
        if len(raw) > VIEW_CHARS:
            flag(folder, "BD-14", f"SKILL.md is {len(raw)} chars; claude.ai's view tool truncates the middle above {VIEW_CHARS}")
        mm = re.search(r"(?mi)^\*\*(purpose|triggers?)\*\*|^#{1,6}\s*when to use\b", body)
        if mm:
            flag(folder, "BD-1", "Purpose/Triggers/When-to-use block likely restates the description (check)", bln(mm.start()))
        mm = re.search(r"(?i)\b(pre-rename|renamed (on|\d)|changelog|history\b|deleted \d{4}-)", body)
        if mm:
            flag(folder, "BD-5", "changelog/history language in body (check)", bln(mm.start()))
        mm = re.search(r"(?i)\b(as of|before|after|until)\s+(?:[a-z]+\s+)?(?:19|20)\d\d\b", body)
        if mm:
            flag(folder, "BD-5", "time-sensitive statement in body (check)", bln(mm.start()))
        mm = re.search(r"(?i)\byour project'?s?\b", body)
        if mm:
            flag(folder, "BD-6", "unresolved 'your project' placeholder", bln(mm.start()))
        if "\\`" in body:
            flag(folder, "BD-11", "escaped backticks in body", bln(body.find("\\`")))
        mm = re.search(r"\b(?:scripts|references|assets)\\[\w.]", body)
        if mm:
            flag(folder, "BD-25", "backslash path; use forward slashes", bln(mm.start()))
        for other in sorted(all_names):
            mm = re.search(rf"(?<![\w/.-]){re.escape(other)}\.md\b", body)
            if mm:
                flag(folder, "BD-7", f"'{other}.md' - skill names take no .md suffix (check)", bln(mm.start()))
        first_ref = {}
        for mm in re.finditer(r"\b((?:references|scripts|assets)/[\w./-]+)", body):
            first_ref.setdefault(mm.group(1), bln(mm.start()))
        for ref, line in sorted(first_ref.items()):
            if not (p.parent / ref.rstrip(".,)")).exists():
                flag(folder, "BD-7", f"referenced file does not exist: {ref} (check)", line)
        first_tok = {}
        for mm in re.finditer(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", body):
            first_tok.setdefault(mm.group(1), bln(mm.start()))
        for tok, line in sorted(first_tok.items()):
            if tok not in all_names and prefix_count.get(tok.split("-")[0], 0) >= 2:
                flag(folder, "XS-3", f"possible dangling skill reference: {tok} (check)", line)
        refs_dir = p.parent / "references"
        if refs_dir.is_dir():
            ref_files = sorted(refs_dir.glob("*.md"))
            for r in ref_files:
                rb = r.read_bytes()
                rt = rb.decode("utf-8", errors="replace")
                files.append((folder, f"references/{r.name}", rt.count("\n") + 1, hashlib.sha256(rb).hexdigest()[:12]))
                if rt.count("\n") > TOC_LINES and not re.search(r"(?mi)^#+\s*(table of )?contents", rt):
                    flag(folder, "BD-14", f"references/{r.name} is over {TOC_LINES} lines without a contents list", loc=f"references/{r.name}")
                if len(rt) > VIEW_CHARS:
                    flag(folder, "BD-14", f"references/{r.name} is {len(rt)} chars; the view tool truncates the middle above {VIEW_CHARS}", loc=f"references/{r.name}")
                for other in ref_files:
                    if other != r and re.search(rf"(?<![\w-]){re.escape(other.name)}\b", rt):
                        flag(folder, "BD-14", f"references/{r.name} points to references/{other.name}: keep references one level deep (check)", loc=f"references/{r.name}")
        if [q for q in p.parent.parents if q in names_by_dir]:
            flag(folder, "FM-12", "nested SKILL.md inside another skill (API/claude.ai reject; only Claude Code loads it)")

        toks = re.findall(r"[a-z0-9]+", desc.lower())
        desc_tokens[folder] = {(a, b) for a, b in zip(toks, toks[1:])
                               if a not in STOP and b not in STOP and len(a) > 2 and len(b) > 2}
        rows.append((folder, name or folder, dw, (len(name) + len(desc)) // 4, blines, len(body.split()), btok))
    return rows, flags, desc_tokens, files, cands


def flag_key(f):
    skill, rule, line, loc, msg = f
    prefix, num = rule.split("-")
    return (skill, RANK.get(prefix, 9), int(num), line or 0, loc or "", msg)


args = sys.argv[1:]
baseline = None
if "--baseline" in args:
    i = args.index("--baseline")
    baseline = args[i + 1]
    del args[i:i + 2]
save_dir = None
if "--save-dir" in args:
    i = args.index("--save-dir")
    save_dir = args[i + 1]
    del args[i:i + 2]
if "--save" in args:
    args.remove("--save")
    save_dir = save_dir or ("/tmp/skill-audit" if os.path.isdir("/tmp")
                            else os.path.join(tempfile.gettempdir(), "skill-audit"))
rows, flags, desc_tokens, files, cands = scan(args[0] if args else ".")
real_stdout, buf = sys.stdout, io.StringIO()
if save_dir:
    sys.stdout = buf

print(f"{'skill':32}{'descW':>6}{'meta~tok':>9}{'bodyL':>7}{'bodyW':>7}{'body~tok':>9}")
for r in sorted(rows, key=lambda r: (-r[6], r[0])):
    print(f"{r[1][:31]:32}{r[2]:>6}{r[3]:>9}{r[4]:>7}{r[5]:>7}{r[6]:>9}")
print(f"\nTOTAL always-on metadata ~tokens: {sum(r[3] for r in rows)}  (skills: {len(rows)})")
print("(~tokens = chars/4, static text only; trigger frequency and extra file reads are not measured)")

print("\nFLAGS (id = skill:RULE:Lline; copy these ids into the report verbatim)")
if not flags:
    print("  none")
seen_ids = collections.Counter()
for f in sorted(flags, key=flag_key):
    skill, rule, line, loc, msg = f
    base = f"{skill}:{rule}:{'L' + str(line) if line else (loc or 'file')}"
    seen_ids[base] += 1
    fid = base if seen_ids[base] == 1 else f"{base}+{seen_ids[base]}"
    print(f"  {fid:46} {msg}")

shared = collections.defaultdict(set)
for skill, bigrams in desc_tokens.items():
    for bg in bigrams:
        shared[bg].add(skill)
collisions = sorted(((" ".join(bg), sorted(s)) for bg, s in shared.items() if len(s) > 1),
                    key=lambda x: (-len(x[1]), x[0]))
print("\nSHARED DESCRIPTION PHRASES (possible trigger collisions, XS-4: check)")
if not collisions:
    print("  none")
for phrase, skills in collisions[:20]:
    print(f"  '{phrase}': {', '.join(skills)}")

print("\nCANDIDATE CUTS (upper bounds, ~tokens saved per load; they count toward the floor only when the matching rubric question is Yes)")
if not cands:
    print("  none")
ceiling = collections.Counter()
for folder, a, b, rule, label, tok in sorted(cands):
    print(f"  {f'{folder}:CUT:L{a}-L{b}':46} {rule:5} {tok:>5}  {label}")
    ceiling[folder] += tok
for folder in sorted(ceiling):
    print(f"  CEILING {folder}: ~{ceiling[folder]} tokens")
if ceiling:
    print(f"  CEILING all skills: ~{sum(ceiling.values())} tokens")

print("\nINPUT FINGERPRINT (audited files: SKILL.md and references/*.md; identical input gives identical hashes)")
for folder, rel, lines, h in sorted(files):
    print(f"  {folder + '/' + rel:52} {lines:>5} lines  {h}")
allhash = hashlib.sha256(''.join(h for *_, h in sorted(files)).encode()).hexdigest()[:12]
print(f"  ALL {allhash}")

if baseline:
    base_rows, *_ = scan(baseline)
    before = {r[0]: r for r in base_rows}
    after = {r[0]: r for r in rows}
    print("\nBASELINE COMPARISON (estimated tokens; negative = saving)  [NC-2]")
    print(f"{'skill':32}{'d_meta':>8}{'d_body':>8}  verdict")
    tm = tb = regressions = 0
    for k in sorted(set(before) | set(after)):
        if k not in before:
            print(f"{k[:31]:32}{after[k][3]:>+8}{after[k][6]:>+8}  NEW skill (adds always-on metadata)")
            tm += after[k][3]; tb += after[k][6]
        elif k not in after:
            print(f"{k[:31]:32}{-before[k][3]:>+8}{-before[k][6]:>+8}  REMOVED")
            tm -= before[k][3]; tb -= before[k][6]
        else:
            dm, db = after[k][3] - before[k][3], after[k][6] - before[k][6]
            tm += dm; tb += db
            bad = [n for n, d in (("metadata", dm), ("body", db)) if d > 0]
            if bad:
                regressions += 1
            print(f"{k[:31]:32}{dm:>+8}{db:>+8}  " + ("REGRESSION: " + " + ".join(bad) if bad else "ok"))
    print(f"{'TOTAL':32}{tm:>+8}{tb:>+8}  {regressions} regression(s): revert or justify each as an approved Decision")

if save_dir:
    sys.stdout = real_stdout
    text = buf.getvalue()
    sys.stdout.write(text)
    stem = f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{allhash}"
    out_dir = pathlib.Path(save_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    measure_path = out_dir / f"measure-{stem}.txt"
    measure_path.write_text(text, encoding="utf-8")
    print(f"SAVED measure output: {measure_path}", file=sys.stderr)
    print(f"REPORT STEM: {out_dir / ('audit-' + stem)}", file=sys.stderr)
