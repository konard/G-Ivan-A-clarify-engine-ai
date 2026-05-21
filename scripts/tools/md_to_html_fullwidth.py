#!/usr/bin/env python
"""Convert a Markdown research document to standalone full-width HTML."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


STYLE = """
html {
  box-sizing: border-box;
}
*, *::before, *::after {
  box-sizing: inherit;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 13px;
  line-height: 1.4;
  margin: 0;
  padding: 12px;
  width: 100vw;
  max-width: none;
  overflow-x: hidden;
}
main {
  width: 100vw;
  max-width: none;
  padding: 0;
  margin: 0;
}
.table-wrap {
  width: 100%;
  overflow-x: auto;
}
table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 11px;
  margin: 8px 0 16px;
}
th, td {
  border: 1px solid #ddd;
  padding: 4px 6px;
  text-align: left;
  vertical-align: top;
  min-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
th {
  background: #f5f5f5;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 10;
}
pre {
  overflow-x: auto;
  padding: 12px;
  background: #f6f8fa;
}
code {
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
}
blockquote {
  border-left: 4px solid #d0d7de;
  margin-left: 0;
  padding-left: 12px;
  color: #57606a;
}
a {
  color: #0969da;
}
@media (prefers-color-scheme: dark) {
  body { background: #1e1e1e; color: #e0e0e0; }
  th { background: #2d2d2d; }
  td, th { border-color: #444; }
  pre { background: #2d2d2d; }
  blockquote { border-left-color: #444; color: #b7b7b7; }
  a { color: #7db7ff; }
}
""".strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def render_table(lines: list[str]) -> str:
    header = split_table_row(lines[0])
    body = [split_table_row(line) for line in lines[2:]]
    parts = ["<div class=\"table-wrap\">", "<table>", "<thead><tr>"]
    parts.extend(f"<th>{inline_markdown(cell)}</th>" for cell in header)
    parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body:
        parts.append("<tr>")
        parts.extend(f"<td>{inline_markdown(cell)}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "\n".join(parts)


def render_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    i = 0

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and lines[i + 1].strip().startswith("|")
            and is_separator(lines[i + 1])
        ):
            flush_paragraph()
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            output.append(render_table(table_lines))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            title = heading.group(2)
            output.append(f'<h{level} id="{slugify(title)}">{inline_markdown(title)}</h{level}>')
        elif stripped == "---":
            flush_paragraph()
            output.append("<hr>")
        elif stripped.startswith(">"):
            flush_paragraph()
            output.append(f"<blockquote>{inline_markdown(stripped.lstrip('> '))}</blockquote>")
        elif stripped.startswith("- "):
            flush_paragraph()
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            output.append("<ul>")
            output.extend(f"<li>{inline_markdown(item)}</li>" for item in items)
            output.append("</ul>")
            continue
        elif stripped:
            paragraph.append(stripped)
        else:
            flush_paragraph()
        i += 1

    flush_paragraph()
    return "\n".join(output)


def convert(input_path: Path, output_path: Path) -> None:
    markdown = input_path.read_text(encoding="utf-8")
    body = render_markdown(markdown)
    title = next(
        (line.lstrip("# ").strip() for line in markdown.splitlines() if line.startswith("# ")),
        input_path.stem,
    )
    document = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
{STYLE}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    output = args.output or args.input.with_suffix(".html")
    convert(args.input, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
