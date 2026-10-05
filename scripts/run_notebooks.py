r"""Execute the numbered lab notebooks and preserve real outputs, HTML and logs.

Windows: .venv\Scripts\python.exe scripts/run_notebooks.py
Linux:   .venv/bin/python scripts/run_notebooks.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import jupytext
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="Notebook numbers, e.g. 01 04")
    parser.add_argument("--profile", choices=["lite", "docker"], default="lite")
    parser.add_argument("--backend", default=None, help="Override model; otherwise NB2 uses MPNet and other notebooks use BGE-small")
    parser.add_argument("--timeout", type=int, default=900, help="Maximum seconds per code cell")
    args = parser.parse_args()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["QDRANT_MODE"] = "server" if args.profile == "docker" else "memory"
    os.environ["QDRANT_URL"] = "http://127.0.0.1:6333"
    os.environ["FEAST_PROFILE"] = args.profile
    os.environ["FEAST_REPO"] = str(ROOT / "app" / ("feast_repo_docker" if args.profile == "docker" else "feast_repo"))
    os.environ["EMBEDDING_BACKEND"] = args.backend or "fastembed"
    if args.backend:
        os.environ["NB2_EMBEDDING_BACKEND"] = args.backend
    else:
        os.environ.pop("NB2_EMBEDDING_BACKEND", None)
    os.environ["FASTEMBED_CACHE_PATH"] = str(ROOT / "data" / "model_cache")
    os.environ["HF_HOME"] = str(ROOT / "data" / "hf_cache")
    os.environ["IPYTHONDIR"] = str(ROOT / ".runtime" / "ipython")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(ROOT / ".runtime" / "jupyter")
    Path(os.environ["IPYTHONDIR"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["JUPYTER_RUNTIME_DIR"]).mkdir(parents=True, exist_ok=True)
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    evidence = ROOT / "submission" / "evidence"
    if args.profile == "docker":
        evidence = evidence / "docker"
    if args.backend and args.backend != "fastembed":
        evidence = evidence / args.backend
    evidence.mkdir(parents=True, exist_ok=True)
    summary_path = evidence / "execution.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    failed = False
    for source in sorted((ROOT / "notebooks").glob("[0-9]*.py")):
        if args.only and source.name[:2] not in args.only:
            continue
        notebook = jupytext.read(source)
        notebook.metadata["kernelspec"] = {
            "display_name": "Lab 19 (.venv)", "language": "python", "name": "lab19"
        }
        start = time.perf_counter()
        print(f"RUN {source.stem}", flush=True)
        error = None
        try:
            NotebookClient(
                notebook, timeout=args.timeout, kernel_name="lab19",
                on_cell_start=lambda cell, cell_index: print(f"  Cell {cell_index}", flush=True),
                resources={"metadata": {"path": str(ROOT / "notebooks")}},
            ).execute()
        except Exception as exc:
            error = str(exc)
            failed = True
        # Also save failures: an incomplete run must remain visible.
        nbformat.write(notebook, evidence / f"{source.stem}.ipynb" if args.profile == "docker" or (args.backend and args.backend != "fastembed") else source.with_suffix(".ipynb"))
        html, _ = HTMLExporter().from_notebook_node(notebook)
        (evidence / f"{source.stem}.html").write_text(html, encoding="utf-8")
        lines = []
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type != "code":
                continue
            lines.append(f"--- Cell {i}, execution {cell.execution_count} ---")
            for output in cell.get("outputs", []):
                if output.output_type == "stream":
                    lines.append(output.text)
                elif output.output_type in ("execute_result", "display_data"):
                    lines.append(output.get("data", {}).get("text/plain", ""))
                elif output.output_type == "error":
                    lines.append(f"ERROR: {output.ename}: {output.evalue}")
        (evidence / f"{source.stem}.txt").write_text("\n".join(lines), encoding="utf-8")
        summary[source.stem] = {
            "status": "FAIL" if error else "PASS",
            "seconds": round(time.perf_counter() - start, 2),
            "executed_cells": sum(c.cell_type == "code" and c.execution_count is not None for c in notebook.cells),
            "total_code_cells": sum(c.cell_type == "code" for c in notebook.cells),
            "error": error,
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{summary[source.stem]['status']} {source.stem} ({summary[source.stem]['seconds']}s)", flush=True)
        if error:
            print(error, flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
