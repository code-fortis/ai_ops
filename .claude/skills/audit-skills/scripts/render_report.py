#!/usr/bin/env python3
"""Render an audit report (Markdown subset) to one self-contained HTML file.

Usage: python render_report.py <report.md> [out.html]
Default output is the same path with .html. Handles headings, fenced code, pipe tables,
bullet and numbered lists, rules, paragraphs, and inline code, bold, italics and links.
Standard library only; output follows the viewer's light/dark setting.
"""
import html
import pathlib
import re
import sys

CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--code:#f6f8fa;--accent:#0969da}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;--line:#3d444d;--code:#151b23;--accent:#4493f8}}
body{font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--fg);max-width:980px;margin:2rem auto;padding:0 1rem}
h1,h2,h3{line-height:1.25}h2{border-bottom:1px solid var(--line);padding-bottom:.3rem;margin-top:2rem}
a{color:var(--accent)}hr{border:0;border-top:1px solid var(--line)}
code{font:.9em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--code);padding:.15em .35em;border-radius:4px}
pre{background:var(--code);border:1px solid var(--line);border-radius:6px;padding:.8rem 1rem;overflow-x:auto}pre code{background:none;padding:0}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border:1px solid var(--line);padding:.4rem .6rem;text-align:left;vertical-align:top}th{background:var(--code)}
"""


def inline(text):
    text = html.escape(text, quote=False)
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", text)


def cells(line):
    parts = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in parts]


SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
ITEM = re.compile(r"^\s*([-*]|\d+\.)\s+(.*)$")


def render(md):
    lines, out, para, title, i = md.split("\n"), [], [], None, 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush()
            n = len(m.group(1))
            if title is None and n == 1:
                title = m.group(2)
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            i += 1
            continue
        if re.match(r"^\s*(-{3,}|\*{3,})\s*$", line):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if "|" in line and i + 1 < len(lines) and SEP.match(lines[i + 1]):
            flush()
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                rows.append(cells(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        m = ITEM.match(line)
        if m:
            flush()
            ordered = m.group(1)[0].isdigit()
            items = []
            while i < len(lines):
                mm = ITEM.match(lines[i])
                if mm:
                    items.append(mm.group(2))
                    i += 1
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        if not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return title or "Audit report", "\n".join(out)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    title, body = render(src.read_text(encoding="utf-8"))
    dst.write_text(
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>\n<body>\n{body}\n</body></html>\n",
        encoding="utf-8")
    print(f"WROTE {dst}")


if __name__ == "__main__":
    main()
