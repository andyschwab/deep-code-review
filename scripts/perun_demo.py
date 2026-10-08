#!/usr/bin/env python3
"""Offline 60-second demo: score the shipped planted-bug fixture, then quote the shipped benchmark.

  perun_demo.py [--results PATH]

Planted bugs and expected findings come from the heldout fixture's ground-truth.json, scored by
score_review.py (no network, no API key, no model call). The benchmark line is the first `BLUF:` line of
the bench results file, copied verbatim with its path; if the file or line is missing it prints
"benchmark: see docs" and never a number. Stdlib only. Exit 0.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_review as sr  # noqa: E402

TRUTH = HERE / "eval-fixtures/heldout/pr1354-ops-scripts/ground-truth.json"
RESULTS = HERE / "eval-fixtures/bench/results.md"


def benchmark(path: Path) -> str:
    try:
        m = re.search(r"^BLUF:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)
    except OSError:
        m = None
    return f"benchmark (copied from scripts/eval-fixtures/bench/results.md): {m.group(1)}" if m else "benchmark: see docs"


def render(truth: dict, results: Path) -> str:
    bugs = truth["bugs"]
    rep = sr.score(truth, [{"file": b["file"], "text": b["example"]} for b in bugs])
    out = [f"Planted bugs: {len(bugs)} (fixture: scripts/eval-fixtures/heldout/pr1354-ops-scripts)"]
    out += [f"  {b['id']} {b['file']}: {b['bug']}" for b in bugs]
    out.append(f"A Perun-style review, per the shipped expected findings, catches {len(rep['hit'])} of {len(bugs)}: {', '.join(rep['hit'])}.")
    out.append("(Scored offline by scripts/score_review.py against the shipped example findings; no model was run, so this shows the method, not a live result.)")
    out.append(benchmark(results))
    return "\n".join(out)


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results", type=Path, default=RESULTS)
    a = ap.parse_args(argv)
    print(render(json.loads(TRUTH.read_text(encoding="utf-8")), a.results))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
