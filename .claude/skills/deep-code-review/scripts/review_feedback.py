#!/usr/bin/env python3
"""review_feedback.py -- repo-local accept/dismiss ledger for review findings.

  record  --id F3 --rule <rule> --verdict accept|dismiss --severity <sev> [--area B] [--reason "..."]
  summary [--min-dismissals 3] [--json]

record appends one JSON line to the ledger (default .review/feedback.jsonl, override with --ledger or
$REVIEW_FEEDBACK_LEDGER). summary prints per-rule accept-rate (telemetry) and SUGGESTED REVIEW.md
rules: a rule is suggested only when it was dismissed at least --min-dismissals times and never
accepted, and never when any of its rows is safety-floor (severity Blocker/Critical, or area in
B C D N Q T: security, LLM/agent, data integrity, secrets, privacy, tenancy). Suggestions are text for
a human to paste into REVIEW.md; this script never writes it, so nothing is silenced automatically.
Side effects: record creates the ledger directory and appends. Reasons are free text: keep names and
identifiers out, and keep the ledger out of public commits. Exits non-zero on a bad ledger line
(fail closed).
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SEVERITIES = ("Blocker", "Critical", "High", "Medium", "Low", "Nit")
SAFETY_SEV = {"Blocker", "Critical"}
SAFETY_AREAS = set("BCDNQT")
DEFAULT_LEDGER = ".review/feedback.jsonl"


def is_safety(row):
    return row["severity"] in SAFETY_SEV or row.get("area", "") in SAFETY_AREAS


def load(path):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            assert r["verdict"] in ("accept", "dismiss") and r["severity"] in SEVERITIES and r["rule"]
        except (ValueError, KeyError, AssertionError, TypeError):
            sys.exit(f"review_feedback: bad ledger line {n} in {path} (fail closed)")
        rows.append(r)
    return rows


def summarize(rows, min_dismissals=3):
    by = defaultdict(list)
    for r in rows:
        by[r["rule"]].append(r)
    out = []
    for rule, rs in sorted(by.items()):
        acc = sum(r["verdict"] == "accept" for r in rs)
        dis = len(rs) - acc
        safety = any(is_safety(r) for r in rs)
        out.append({
            "rule": rule, "accepted": acc, "dismissed": dis, "accept_rate": round(acc / len(rs), 2),
            "safety_floor": safety,
            "suggest": (not safety) and acc == 0 and dis >= min_dismissals,
            "reasons": sorted({r["reason"] for r in rs if r.get("reason") and r["verdict"] == "dismiss"}),
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", default=os.environ.get("REVIEW_FEEDBACK_LEDGER", DEFAULT_LEDGER))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--id", required=True)
    r.add_argument("--rule", required=True)
    r.add_argument("--verdict", required=True, choices=("accept", "dismiss"))
    r.add_argument("--severity", required=True, choices=SEVERITIES)
    r.add_argument("--area", default="", help="domain letter A-W")
    r.add_argument("--reason", default="")
    s = sub.add_parser("summary")
    s.add_argument("--min-dismissals", type=int, default=3)
    s.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "record":
        row = {k: getattr(a, k) for k in ("id", "rule", "verdict", "severity", "area", "reason")}
        Path(a.ledger).parent.mkdir(parents=True, exist_ok=True)
        with open(a.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return 0
    res = summarize(load(a.ledger), a.min_dismissals)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    print("rule\taccepted\tdismissed\taccept_rate\tnote")
    for x in res:
        note = "safety floor: never suppressed" if x["safety_floor"] else ""
        print(f"{x['rule']}\t{x['accepted']}\t{x['dismissed']}\t{x['accept_rate']}\t{note}")
    sug = [x for x in res if x["suggest"]]
    if sug:
        print("\nSuggested REVIEW.md rules (human approves; paste or discard):")
    for x in sug:
        why = "; ".join(x["reasons"]) or "no reason recorded"
        print(f"- skip: {x['rule']} (dismissed {x['dismissed']}x, accepted 0x; reasons: {why})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
