#!/usr/bin/env python3
"""tracker_weekly_update.py - draft the weekly project update (markdown on stdout) from the last 7 days of PRs.

Sections: suggested health, Delivered (merged PRs by tracker ID), Next (open PRs), Blockers (open PRs with
changes requested), Untracked (merged PRs with no ID). Health is a suggestion only; the DRI decides.
Never posts anything: a human or agent posts the text via the tracker UI or MCP.
Usage: tracker_weekly_update.py [--key ACME] [--days 7]   Env: TRACKER_KEY.
Side effects: none (gh reads only). Without gh it prints a "not checked" line and exits 0.
"""
import argparse
import datetime as dt
import os
import sys

from tracker_check import gh_prs, id_regex


def draft(merged, opened, rx):
    def ids(p):
        return sorted(set(rx.findall("%s\n%s" % (p.get("title") or "", p.get("body") or ""))))

    def line(p):
        return "- %s (repo PR %d)" % (p["title"], p["number"])

    def sec(title, lines):
        return ["", "### " + title] + (lines or ["- none"])

    blockers = [p for p in opened if p.get("reviewDecision") == "CHANGES_REQUESTED"]
    health = "At risk" if blockers or not merged else "On track"
    reason = ("changes requested on %d open PR(s)" % len(blockers) if blockers
              else "nothing merged this period" if not merged else "merged work and no blocked PRs")
    out = ["## Weekly update", "", "Suggested health: %s (%s; suggestion, the DRI decides)" % (health, reason)]
    out += sec("Delivered", ["- %s: %s (repo PR %d)" % (", ".join(ids(p)), p["title"], p["number"])
                             for p in merged if ids(p)])
    out += sec("Next", [line(p) for p in opened if not p.get("isDraft")])
    out += sec("Blockers", [line(p) for p in blockers])
    untracked = [line(p) for p in merged if not ids(p)]
    if untracked:
        out += sec("Untracked (no tracker ID; add one before posting)", untracked)
    return "\n".join(out)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("--key", default=os.environ.get("TRACKER_KEY"))
    a.add_argument("--days", type=int, default=7)
    args = a.parse_args(argv)
    since = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    merged, opened = gh_prs("merged", since), gh_prs("open")
    if merged is None or opened is None:
        print("NOT CHECKED: PRs (gh missing, unauthenticated, or failed); no draft produced")
        return 0
    print(draft(merged, opened, id_regex(args.key)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
