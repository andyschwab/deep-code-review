#!/usr/bin/env python3
"""Build the two tool-result / startup variants run.sh checks, from the frozen fixture (stdlib, deterministic, placeholder text only).

Usage: python3 overlay.py OUTDIR   (writes OUTDIR/fire/ and OUTDIR/quiet/, each with session.jsonl, session/subagents/ and project/)
The frozen session is copied, then tool results are injected on the main thread (length is what token_report reads; the body is the word
"synthetic" repeated). `fire` has one Bash result far past the 10,000-char cap, one at 9,999 (below the floor, ignored), a Read and an MCP
result, plus a 112,000-byte CLAUDE.md. `quiet` clips every result to at or below 10,000 chars (the floor itself or less, never over it) and has a 2,000-byte
CLAUDE.md. Injected results do not change the fixture's token usage, which stays the frozen arithmetic: the tool-result figures are
fixture numbers for the detectors, not a model of what those results would have cost.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FLOOR = 10_000
# (main turn index, tool name, result chars)
RESULTS = ((1, "Bash", 150_000), (3, "Bash", 9_999), (10, "Read", 20_000), (12, "mcp__synthetic__search", 15_000))


def body(n):
    return ("synthetic " * (n // 10 + 1))[:n]


def inject(rows, clip):
    out = []
    for i, row in enumerate(rows):
        out.append(row)
        for turn, name, n in RESULTS:
            if turn == i:
                tid = f"m{i}"
                row["message"]["content"].append({"type": "tool_use", "id": tid, "name": name, "input": {}})
                out.append({"type": "user", "isSidechain": False, "timestamp": row["timestamp"],
                            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid,
                                                                      "content": body(min(n, FLOOR) if clip else n)}]}})
    return out


def build(dest, clip, claude_md_bytes):
    os.makedirs(f"{dest}/project")
    shutil.copytree(f"{HERE}/session/subagents", f"{dest}/session/subagents")
    with open(f"{HERE}/session.jsonl", encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh]
    with open(f"{dest}/session.jsonl", "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in inject(rows, clip))
    with open(f"{dest}/project/CLAUDE.md", "w", encoding="utf-8") as fh:
        fh.write(body(claude_md_bytes))


if __name__ == "__main__":
    build(f"{sys.argv[1]}/fire", False, 112_000)
    build(f"{sys.argv[1]}/quiet", True, 2_000)
