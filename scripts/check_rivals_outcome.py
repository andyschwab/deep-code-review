#!/usr/bin/env python3
"""Fail if a Perun-vs-rival row in docs/perun-vs-rivals.md has no outcome-metric field.

Structure it parses: the first table (header has `Bench dir`) lists one comparison per row with a skill in
column 1 and its bench directories, backticked, in column 3; the audit table (header has `Outcome measured`)
must hold, for each bench directory, a row whose first cell is that skill followed by backticked directories including it (exact match). An empty first table fails.
Audit rule per row: Type is Outcome, Proxy, Mixed or Not a comparison; Outcome and Mixed need an
`Outcome measured` cell starting `Measured:`; Proxy needs one starting `None`, so a proxy cannot claim a
measurement. A missing table fails closed. Usage: check_rivals_outcome.py docs/perun-vs-rivals.md
Exit 1 and one line per problem on failure. Side effects: none."""
import re
import sys
from pathlib import Path

TYPES = ("Outcome", "Proxy", "Mixed", "Not a comparison")


def tables(text):
    """Yield (header_cells, [row_cells]) for each markdown table (header, separator, rows)."""
    lines = [re.sub(r"^[\s>]*", "", x) for x in text.splitlines()] + [""]
    i = 0
    while i < len(lines) - 1:
        if lines[i].startswith("|") and re.match(r"\|[\s:|-]+\|?$", lines[i + 1]):
            j = i + 2
            while lines[j].startswith("|"):
                j += 1
            yield cells(lines[i]), [cells(x) for x in lines[i + 2:j]]
            i = j
        else:
            i += 1


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def check(text):
    """Return a list of problem strings; empty means every row carries an outcome-metric field."""
    top = audit = None
    for head, rows in tables(text):
        if any("Bench dir" in h for h in head) and top is None:
            top = rows
        if any("Outcome measured" in h for h in head) and audit is None:
            audit = (head, rows)
    if top is None or audit is None:
        return ["missing table: the first table (header `Bench dir`) or the audit table (header `Outcome measured`)"]
    head, rows = audit
    if not top:
        return ["the first table (header `Bench dir`) has no rows"]
    try:
        ti, oi = head.index(next(h for h in head if h.startswith("Type"))), head.index("Outcome measured")
    except (StopIteration, ValueError):
        return ["audit table header needs a `Type` and an `Outcome measured` column"]
    bad = []
    named = [(a[0].split("`")[0].strip(), set(re.findall(r"`([^`]+)`", a[0]))) for a in rows]
    for r in top:
        dirs = re.findall(r"`([^`]+)`", r[2]) if len(r) > 2 else []
        if not dirs:
            bad.append(f"row has no bench dir: {r[0]}")
        for d in dirs:
            if not any(r[0] and r[0] == skill and d in ds for skill, ds in named):
                bad.append(f"row has no outcome-metric audit row: {r[0]} {d}")
    for a in rows:
        if len(a) <= max(ti, oi):
            bad.append(f"audit row has too few cells: {a[0]}")
            continue
        typ, out = a[ti], a[oi]
        if typ not in TYPES or not out:
            bad.append(f"audit row needs a Type in {TYPES} and an outcome cell: {a[0]}")
        elif typ in ("Outcome", "Mixed") and not (out.startswith("Measured:") and out[9:].strip()):
            bad.append(f"{typ} row must start its outcome cell with `Measured:` and say what: {a[0]}")
        elif typ == "Proxy" and not out.startswith("None"):
            bad.append(f"Proxy row must start its outcome cell with `None`: {a[0]}")
    return bad


if __name__ == "__main__":
    problems = check(Path(sys.argv[1]).read_text())
    print("\n".join(problems))
    sys.exit(1 if problems else 0)
