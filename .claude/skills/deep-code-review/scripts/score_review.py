#!/usr/bin/env python3
"""Score a review's findings against a ground-truth file: recall and precision under an FP budget.

  score_review.py GROUND_TRUTH.json FINDINGS.json [--max-fp N]
  score_review.py --selftest

FINDINGS.json is a list of objects with at least `file` and `text` (the bug mechanism); `line` and
`severity` are optional and ignored. GROUND_TRUTH.json has `matcher_version` and `bugs`, each with
`id`, `file`, and `match`, a regex naming the root-cause mechanism.

A finding matches a bug only when its file basename equals the bug's AND its text matches the bug's
`match` regex (mechanism, not location: a right-file finding with the wrong mechanism is a miss).
Several findings on one bug earn one recall credit (dedup). Every finding matching no bug charges the
FP budget; unmatched is not automatically false (human-label a sample), so the report calls it
`unmatched`, not `false_positive`.

Report (JSON on stdout): recall, strict precision (matched findings / findings), hit and missed bug
ids, unmatched count, matcher_version. Exit 0 ok, 1 when --max-fp is set and unmatched exceeds it,
2 usage/bad input. The matcher is part of the instrument: bump `matcher_version` in the ground truth
on any `match` change; --selftest proves the instrument scores 1.0 on each bug's `example` finding
and 0 on wrong-mechanism and wrong-file findings. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def score(truth: dict, findings: list) -> dict:
    bugs = truth["bugs"]
    hit, matched = set(), 0
    for f in findings:
        base, text = Path(str(f.get("file", ""))).name, str(f.get("text", ""))
        ids = [b["id"] for b in bugs if Path(b["file"]).name == base and re.search(b["match"], text, re.I)]
        matched += bool(ids)
        hit.update(ids)
    return {"matcher_version": truth.get("matcher_version"), "bugs": len(bugs), "findings": len(findings),
            "hit": sorted(hit), "missed": sorted(b["id"] for b in bugs if b["id"] not in hit),
            "recall": round(len(hit) / len(bugs), 4) if bugs else None,
            "precision": round(matched / len(findings), 4) if findings else None,
            "unmatched": len(findings) - matched}


def selftest(truth: dict) -> bool:
    good = [{"file": b["file"], "text": b["example"]} for b in truth["bugs"]]
    wrong = [{"file": b["file"], "text": "style nit: add a comment here"} for b in truth["bugs"]]
    other_file = [{"file": "unrelated.sh", "text": b["example"]} for b in truth["bugs"]]
    g, w, o = score(truth, good), score(truth, wrong), score(truth, other_file)
    return g["recall"] == 1.0 and g["precision"] == 1.0 and w["recall"] == 0 and o["recall"] == 0 and w["unmatched"] == len(wrong)


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--max-fp", type=int)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    default = Path(__file__).resolve().parent / "fixtures/heldout/pr1354-ops-scripts/ground-truth.json"
    if a.selftest:
        ok = selftest(json.loads(default.read_text(encoding="utf-8")))
        print("score_review selftest:", "ok" if ok else "FAIL")
        return 0 if ok else 1
    if len(a.paths) != 2:
        ap.error("need GROUND_TRUTH.json FINDINGS.json")
    try:
        rep = score(json.loads(Path(a.paths[0]).read_text(encoding="utf-8")), json.loads(Path(a.paths[1]).read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"score_review: bad input ({type(e).__name__})", file=sys.stderr)
        return 2
    print(json.dumps(rep, indent=1))
    return 1 if a.max_fp is not None and rep["unmatched"] > a.max_fp else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
