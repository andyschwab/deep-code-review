#!/usr/bin/env python3
"""status_update_lint.py --file F — check a leadership status update against references/leadership-status-update.md.

Checks: all seven sections present with the Detail link last; bottom line has a timestamp with time zone and a
number; "What moved" has a before -> after line with a delta; lines before Detail carry no `#123`, PR, branch, CI,
pipeline or commit terms, no effort counts and no "next week" promises; the Decision line recommends (or says
none); plus the unverified "live"/"done" check from status_vocab_lint. Prints `L<n>: <problem>` per hit; exit 1
on any hit, 0 clean, 2 usage/unreadable. Limits: regex heuristics on text shape; a clean run proves the shape
only, never that a number is true.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import status_vocab_lint  # noqa: E402

LABELS = ["bottom line", "what moved", "what users can now do", "health", "slipped", "decision needed", "detail"]
LABEL = re.compile(r"^[\s>#*_\-]*(bottom line|what moved|what users can now do|health|slipped|decision needed|detail)\b", re.I)
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{1,2}:\d{2}\s*(Z|UTC|GMT|[A-Z]{2,4}|[+-]\d{2}:?\d{2})(?![A-Za-z])")
MOVED = re.compile(r"(→|->).*\(\s*[+\-−±]?\d")
JARGON = re.compile(r"#\d+|\bPRs?\b|pull request|\bbranch(es)?\b|\b(feat|fix|chore)/\S+|\bCI\b|pipeline|\bcommits?\b|\bmerged?\b", re.I)
EFFORT = re.compile(r"\b\d+\s+(PRs?|commits?|tasks?|tickets?|issues?|lines|story points)\b|\d+\s*%\s*complete", re.I)
PROMISE = re.compile(r"next (week|sprint|month)|coming (soon|next)|ships? next", re.I)


def lint(text):
    """Return [(line_no, problem)] for a status update; empty list means the shape is right."""
    lines = text.splitlines()
    hits, sec_at = [], {}
    for i, ln in enumerate(lines):
        m = LABEL.match(ln)
        if m and m.group(1).lower() not in sec_at:
            sec_at[m.group(1).lower()] = i
    first = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if first is None:
        return [(1, "empty update")]
    sec_at.setdefault("bottom line", first)
    for name in LABELS[1:]:
        if name not in sec_at:
            hits.append((1, f"missing section: {name}"))
    end = sec_at.get("detail", len(lines))
    last = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip()), first)
    d = sec_at.get("detail")
    if d is not None and (max(sec_at.values()) != d or len([x for x in lines[d:] if x.strip()]) != 1
                          or "http" not in lines[d]):
        hits.append((d + 1, "Detail must be the last section and hold one link"))
    bl = lines[first]
    if not STAMP.search(bl):
        hits.append((first + 1, "bottom line needs a timestamp with time zone, e.g. 2026-10-12 14:30 PT"))
    if not re.search(r"\d", STAMP.sub("", bl)):
        hits.append((first + 1, "bottom line needs one number, e.g. '20 of 21 requests fixed (was 12, +8)'"))
    if "what moved" in sec_at:
        nxt = min([v for v in sec_at.values() if v > sec_at["what moved"]] + [end])
        if not any(MOVED.search(x) for x in lines[sec_at["what moved"]:nxt]):
            hits.append((sec_at["what moved"] + 1, "What moved needs a 'before → after (delta)' line"))
    if "decision needed" in sec_at:
        i = sec_at["decision needed"]
        d = lines[i]
        if not re.search(r"\bnone\b|\bno decision\b|recommend", d, re.I):
            hits.append((i + 1, "Decision needed must say 'Recommend A ...' first, or 'none'"))
        elif re.search(r"recommend", d, re.I) and not re.search(r"\bB\b", d):
            hits.append((i + 1, "Decision needed must offer an A/B choice"))
    fence = False
    for i in range(end):
        if lines[i].lstrip().startswith("```"):
            fence = not fence
        if fence:
            continue
        for rx, why in ((JARGON, "PR/branch/CI/pipeline jargon before Detail"),
                        (EFFORT, "effort count before Detail"), (PROMISE, "forward promise before Detail")):
            m = rx.search(lines[i])
            if m:
                hits.append((i + 1, f"{why}: '{m.group(0)}'"))
    hits += [(n, f"'{p}' with no verified-on-<page> or journey: reference") for n, p in status_vocab_lint.lint(text)]
    return sorted(hits)


def main(argv):
    if len(argv) != 3 or argv[1] != "--file":
        print("usage: status_update_lint.py --file <update.md>", file=sys.stderr)
        return 2
    try:
        text = open(argv[2], encoding="utf-8").read()
    except (OSError, UnicodeError):
        print("status_update_lint: unreadable input", file=sys.stderr)
        return 2
    hits = lint(text)
    for n, p in hits:
        print(f"L{n}: {p}")
    print(f"status_update_lint: {'%d hit(s)' % len(hits) if hits else 'ok'}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
