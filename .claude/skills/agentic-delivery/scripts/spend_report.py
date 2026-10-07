#!/usr/bin/env python3
"""Group a provider usage export (CSV or JSON file) by API-key-name prefix into per-project spend.

Convention (see agentic-delivery operating-discipline.md): keys or vendor workspaces are named
`<tracker-project-id>-<handle>`. The handle is the text after the LAST hyphen, so project ids may
themselves contain hyphens. A name with no hyphen is reported as `(unattributed)`.

Usage: spend_report.py FILE [--key-field F] [--cost-field F] [--warn AMOUNT] [--json]
No network: reads the file you exported. Rows with no parseable cost are counted as UNPRICED,
never summed as zero. Exit 0 ok, 2 unreadable input or missing fields.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation

KEYS = ("api_key_name", "key_name", "workspace", "name")
COSTS = ("cost_usd", "cost", "amount", "spend")


def load_rows(path):
    """Return a list of dict rows from a .json (list, or object with a list under any key) or CSV file."""
    with open(path, newline="", encoding="utf-8") as fh:
        if path.lower().endswith(".json"):
            data = json.load(fh)
            if isinstance(data, dict):
                data = next((v for v in data.values() if isinstance(v, list)), [])
            return [r for r in data if isinstance(r, dict)]
        return list(csv.DictReader(fh))


def pick(row, names):
    return next((n for n in names if n in row), None)


def project_of(key_name):
    """`ENG-12-jane` -> `ENG-12`; no hyphen -> `(unattributed)`."""
    key_name = (key_name or "").strip()
    return key_name.rsplit("-", 1)[0] if "-" in key_name else "(unattributed)"


def aggregate(rows, key_field=None, cost_field=None):
    """Return (totals {project: Decimal}, unpriced {project: int}). Raises ValueError on missing fields."""
    if not rows:
        return {}, {}
    kf = key_field or pick(rows[0], KEYS)
    cf = cost_field or pick(rows[0], COSTS)
    if kf not in rows[0] or cf not in rows[0]:
        raise ValueError(f"need key and cost columns; found {sorted(rows[0])}")
    totals, unpriced = defaultdict(Decimal), defaultdict(int)
    for r in rows:
        p = project_of(str(r.get(kf) or ""))
        try:
            d = Decimal(str(r.get(cf)).strip().lstrip("$").replace(",", ""))
        except (InvalidOperation, AttributeError):
            d = None
        if d is None or not d.is_finite():  # NaN/Infinity would poison sums and sorting
            unpriced[p] += 1
            totals[p] += Decimal(0)
        else:
            totals[p] += d
    return dict(totals), dict(unpriced)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--key-field")
    ap.add_argument("--cost-field")
    ap.add_argument("--warn", type=Decimal, help="flag projects whose total is at or above this amount")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        totals, unpriced = aggregate(load_rows(a.file), a.key_field, a.cost_field)
    except (OSError, ValueError) as e:
        print(f"spend_report: {e}", file=sys.stderr)
        return 2
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    if a.json:
        print(json.dumps({p: {"total": str(t), "unpriced_rows": unpriced.get(p, 0)} for p, t in ranked}))
        return 0
    for p, t in ranked:
        note = f"  UNPRICED rows: {unpriced[p]}" if p in unpriced else ""
        flag = "  WARN" if a.warn is not None and t >= a.warn else ""
        print(f"{p}\t{t}{note}{flag}")
    print(f"TOTAL\t{sum(totals.values(), Decimal(0))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
