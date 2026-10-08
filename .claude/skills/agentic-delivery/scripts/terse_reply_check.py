#!/usr/bin/env python3
"""Stop hook (OPT-IN, `install.sh --with-terse-replies`): ask for a terser rewrite.

Reads the Stop-hook JSON on stdin and takes `last_assistant_message`. Fenced
code blocks, inline code and quoted/error lines are ignored. The remaining
words are scored: share of filler/article/hedge words plus words inside
pleasantry phrases. Above TERSE_MAX_RATIO (default 0.12) it prints the
documented block response, `{"decision": "block", "reason": ...}`, which sends
the same turn back for a rewrite (https://code.claude.com/docs/en/hooks).

Guards: `stop_hook_active` true means this turn is already a rewrite, so it
allows (at most 1 rewrite per turn). Replies under TERSE_MIN_WORDS (default
25) are allowed. Any error fails open (exit 0, no output). No voice text is
vendored: for a chat-voice style see the public caveman repository,
https://github.com/JuliusBrussee/caveman. Deterministic, stdlib only.
Env: TERSE_MAX_RATIO, TERSE_MIN_WORDS.
"""
import json
import os
import re
import sys

WORDS = set(
    "a an the just really basically actually simply very quite essentially literally "
    "perhaps maybe probably possibly might seems somewhat likely arguably generally "
    "also however additionally furthermore moreover please".split()
)
PHRASES = (
    "sure", "certainly", "of course", "happy to", "glad to", "great question",
    "i hope this helps", "let me know if", "feel free to", "no problem", "absolutely",
    "i'd be happy", "thanks for",
)
REASON = (
    "Reply too wordy ({r:.0%} filler/article/hedge words, limit {m:.0%}). Rewrite "
    "terser: drop articles, filler, hedges and pleasantries; keep every technical "
    "fact, code and error text exact."
)


def strip(text):
    text = re.sub(r"```.*?(```|\Z)", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    keep = [
        ln for ln in text.splitlines()
        if not re.match(r"\s*>", ln) and not re.search(r"\b(Error|Exception|Traceback|FAILED)\b|\berror:", ln)
    ]
    return "\n".join(keep)


def ratio(text):
    low = strip(text).lower()
    words = re.findall(r"[a-z']+", low)
    if not words:
        return 0.0, 0
    hits = sum(w in WORDS for w in words)
    for p in PHRASES:
        hits += low.count(p) * len(p.split())
    return hits / len(words), len(words)


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("stop_hook_active"):
            return 0
        limit = float(os.environ.get("TERSE_MAX_RATIO", "0.12"))
        r, n = ratio(data.get("last_assistant_message") or "")
        if n >= int(os.environ.get("TERSE_MIN_WORDS", "25")) and r > limit:
            print(json.dumps({"decision": "block", "reason": REASON.format(r=r, m=limit)}))
    except Exception:  # fail open
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
