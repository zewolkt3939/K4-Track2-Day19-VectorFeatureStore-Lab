"""Verify executed deliverables, then record smoke, full benchmark and bonus runs."""
from __future__ import annotations

import json
import argparse
import os
import subprocess
import sys
from pathlib import Path

import jupytext

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "submission" / "evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebooks-only", action="store_true", help="Check notebook completeness and source consistency")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.update({
        "PYTHONIOENCODING": "utf-8", "QDRANT_MODE": "memory",
        "EMBEDDING_BACKEND": "fastembed",
        "FASTEMBED_CACHE_PATH": str(ROOT / "data" / "model_cache"),
        "HF_HOME": str(ROOT / "data" / "hf_cache"),
    })
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    sources = sorted((ROOT / "notebooks").glob("[0-9]*.py"))
    assert len(sources) == 8, "Expected eight numbered notebook sources"
    for source in sources:
        path = source.with_suffix(".ipynb")
        if not path.exists():
            raise RuntimeError(f"Missing executed notebook: {path}")
        notebook = json.loads(path.read_text(encoding="utf-8"))
        code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        assert all(c["execution_count"] is not None for c in code), f"Unexecuted cells in {path}"
        assert not any(o["output_type"] == "error" for c in code for o in c["outputs"]), f"Errors in {path}"
        expected = [c.source for c in jupytext.read(source).cells]
        actual = ["".join(c["source"]) for c in notebook["cells"]]
        assert expected == actual, f"Notebook source differs from {source}; execute it again"
    summary["notebooks"] = {"status": "PASS", "count": len(sources)}
    if args.notebooks_only:
        print("PASS — eight notebooks, all cells executed, no errors, sources match")
        return 0
    commands = {
        "smoke": ["scripts/verify_lite.py"],
        "benchmark": ["scripts/benchmark.py", "--output", "submission/evidence/benchmark.json"],
        "bonus": ["bonus/demo.py"],
    }
    for label, args in commands.items():
        print(f"RUN {label}", flush=True)
        with (OUT / f"{label}.txt").open("w", encoding="utf-8") as log:
            result = subprocess.run([sys.executable, "-u", *args], stdout=log, stderr=subprocess.STDOUT)
        summary[label] = {"status": "PASS" if result.returncode == 0 else "FAIL",
                          "exit_code": result.returncode}
        (OUT / "checks.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"{summary[label]['status']} {label}", flush=True)
    return int(any(row["status"] != "PASS" for row in summary.values()))


if __name__ == "__main__":
    raise SystemExit(main())
