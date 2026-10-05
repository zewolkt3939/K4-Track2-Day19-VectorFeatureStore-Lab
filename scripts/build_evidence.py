"""Create compact output-only pages for browser screenshots from executed notebooks."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "submission" / "evidence"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    links = []
    paths = sorted((ROOT / "notebooks").glob("[0-9]*.ipynb")) + sorted(OUT.rglob("[0-9]*.ipynb"))
    for path in paths:
        target = OUT if path.parent == ROOT / "notebooks" else path.parent
        profile = "Lite · BGE-small" if target == OUT else str(target.relative_to(OUT))
        notebook = json.loads(path.read_text(encoding="utf-8"))
        sections = []
        heading = ""
        for cell in notebook["cells"]:
            source = "".join(cell["source"])
            if cell["cell_type"] == "markdown":
                titles = [line.lstrip("# ") for line in source.splitlines() if line.startswith("## ")]
                if titles:
                    heading = titles[0]
                continue
            outputs = []
            for item in cell.get("outputs", []):
                if item["output_type"] == "stream":
                    value = "".join(item["text"])
                elif item["output_type"] in ("execute_result", "display_data"):
                    value = "".join(item["data"].get("text/plain", []))
                elif item["output_type"] == "error":
                    value = f"ERROR {item['ename']}: {item['evalue']}"
                else:
                    continue
                # CLI color codes are not meaningful in an HTML output viewer.
                outputs.append(re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value))
            if outputs:
                sections.append(f"<section><h2>{html.escape(heading)} — In [{cell['execution_count']}]</h2>"
                                f"<pre>{html.escape(''.join(outputs))}</pre></section>")
        name = f"{path.stem}_outputs.html"
        page = f"""<!doctype html><html lang="vi"><meta charset="utf-8">
<title>{path.stem} — executed evidence</title>
<style>body{{max-width:1160px;margin:24px auto;padding:0 24px;background:#f6f8fb;color:#162033;font:16px Arial,sans-serif}}
h1{{font-size:28px}}h2{{font-size:18px;color:#174c79}}section{{background:white;border:1px solid #ccd6e3;border-radius:8px;padding:10px 20px;margin:14px 0}}
pre{{font:14px Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}}a{{color:#174c79}}</style>
<h1>{html.escape(path.stem)}</h1>
<p>Minh chứng từ output notebook đã thực thi — Python 3.12 · {html.escape(profile)} · dữ liệu tổng hợp.</p>
<p><a href="{path.stem}.html">Notebook đầy đủ</a> · <a href="{path.stem}.txt">Log gốc</a></p>
{''.join(sections)}</html>"""
        (target / name).write_text(page, encoding="utf-8")
        link = (target / name).relative_to(OUT).as_posix()
        links.append(f'<li><a href="{link}">{html.escape(profile)} — {path.stem}</a></li>')
    (OUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Lab 19 evidence</title>'
        '<h1>Lab 19 — kết quả thực thi</h1><ul>' + ''.join(links) + '</ul>', encoding="utf-8"
    )
    print(f"Generated {len(links)} output pages in {OUT}")


if __name__ == "__main__":
    main()
