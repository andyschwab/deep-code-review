#!/usr/bin/env python3
"""Context audit: which always-loaded files cost tokens on every turn, how big, and one cut per top offender. Read-only, offline.

Sources: CLAUDE.md files, MEMORY.md indexes and installed skill descriptions (the name and description frontmatter of each
<skills-dir>/*/SKILL.md, which sit in context every turn). Instruction and memory files count raw on-disk bytes; a skill row counts its description bytes only (what loads, not the file); tokens are bytes/4 (APPROXIMATE, not a tokenizer).

  context_audit.py [PATH...] [--memory-dir DIR]... [--skills-dir DIR]... [--top N] [--index-max N] [--section-max N] [--desc-max N] [--json]

Defaults: the instruction files `token_report.instruction_candidates(".")` finds (CLAUDE.md, AGENTS.md, .claude/CLAUDE.md, user-level
CLAUDE.md, this project's memory MEMORY.md), plus skills in ./.claude/skills and <config dir>/skills; absent defaults are skipped. A file
reached twice (repeat or symlink) counts once. Exit 2 when an explicit PATH, --memory-dir or --skills-dir is missing, a PATH is not a
file, a --memory-dir or --skills-dir is not a directory, or a file cannot be read. Advice: MEMORY.md lines over --index-max (200) chars, CLAUDE.md "## " sections over --section-max
(4000) bytes (move to an on-demand reference), skill descriptions over --desc-max (300) chars, and lines repeated across sources.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import token_report as tr  # noqa: E402  (shared file discovery and the bytes/4 estimate)


def skill_description(text: str) -> str:
    """Return the frontmatter `description:` value (folded/literal blocks, quotes and CRLF handled); '' when absent."""
    m = re.match(r"---\n(.*?)\n---", text.replace("\r\n", "\n"), re.S)
    if not m:
        return ""
    lines = m.group(1).split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("description:"):
            val = ln[len("description:"):].strip()
            parts = ["" if val in (">", "|", ">-", "|-") else val]
            for nxt in lines[i + 1:]:
                if not nxt.startswith((" ", "\t")):
                    break
                parts.append(nxt.strip())
            return " ".join(p for p in parts if p).strip("\"'")
    return ""


def collect(paths, memory_dirs, skills_dirs):
    """Return [{kind, path, bytes, text}], one per distinct file (by resolved path); `bytes` is raw size (a skill: its description bytes), `text` what is loaded.

    A skill's text is its description only. Directories named like a file are skipped under the dir arguments. Raises OSError when a
    chosen file cannot be read.
    """
    cands = [(str(p), "memory" if p.name == "MEMORY.md" else "claude", p) for p in paths]
    for d in memory_dirs:
        cands += [(str(p), "memory", p) for p in sorted(d.rglob("MEMORY.md")) if p.is_file()]
    for d in skills_dirs:
        cands += [(str(p), "skill", p) for p in sorted(d.glob("*/SKILL.md")) if p.is_file()]
    out, seen = [], set()
    for label, kind, p in cands:
        real = p.resolve()
        if real in seen:
            continue
        seen.add(real)
        raw = p.read_bytes()
        text = raw.decode(errors="replace")
        if kind == "skill":
            text = skill_description(text)
            if not text:
                continue
            raw = text.encode()
        out.append({"kind": kind, "path": label, "text": text, "bytes": len(raw)})
    return out


def cut(s, a):
    """One concrete cut for source `s`: (advice, bytes_saved); bytes_saved is 0 when no size-based cut applies."""
    t = s["text"]
    if s["kind"] == "memory":
        long_ = [(n, len(ln)) for n, ln in enumerate(t.splitlines(), 1) if len(ln) > a.index_max]
        if long_:
            saved = sum(c - a.index_max for _, c in long_)
            return f"shorten {len(long_)} index line(s) over {a.index_max} chars (first: line {long_[0][0]}) to one short hook each", saved
        return "index lines already short; delete entries you never act on", 0
    if s["kind"] == "skill":
        n = len(t)
        if n > a.desc_max:
            return f"cut this description from {n} to {a.desc_max} chars (trigger phrases only)", n - a.desc_max
        return "description already short; uninstall the skill if unused", 0
    secs, head, cur = [], "(preamble)", []
    for ln in t.splitlines(True):
        if ln.startswith("## "):
            secs.append((head, sum(len(x.encode()) for x in cur)))
            head, cur = ln.strip(), []
        cur.append(ln)
    secs.append((head, sum(len(x.encode()) for x in cur)))
    h, b = max(secs, key=lambda x: x[1])
    if b > a.section_max:
        return f"move section '{h}' to an on-demand reference file; keep a one-line pointer", max(0, b - 100)
    return f"no section over {a.section_max} bytes; trim the largest, '{h}' ({b} bytes), or drop stale lines", 0


def duplicates(sources, min_len=30):
    """Lines (>= min_len chars, not headings/fences, case and bullet-insensitive) in 2+ non-skill sources: [(line, [paths])]."""
    seen = defaultdict(set)
    for s in sources:
        if s["kind"] == "skill":
            continue
        for ln in s["text"].splitlines():
            k = ln.strip().lstrip("-*0123456789. ").lower()
            if len(k) >= min_len and not k.startswith(("#", "```")):
                seen[k].add(s["path"])
    return sorted(((k, sorted(v)) for k, v in seen.items() if len(v) > 1), key=lambda x: -len(x[0]))


def audit(sources, a):
    """Build the report dict: per-kind totals, ranked top offenders with one cut each, duplicate lines."""
    total = sum(s["bytes"] for s in sources)
    kinds = {}
    for s in sources:
        k = kinds.setdefault(s["kind"], {"sources": 0, "bytes": 0})
        k["sources"] += 1
        k["bytes"] += s["bytes"]
    for k in kinds.values():
        k["tokens_approx"], k["pct"] = tr.est_tokens(k["bytes"]), round(100 * k["bytes"] / (total or 1), 1)
    top = []
    for s in sorted(sources, key=lambda s: -s["bytes"])[: a.top]:
        advice, saved = cut(s, a)
        top.append({"kind": s["kind"], "path": s["path"], "bytes": s["bytes"], "tokens_approx": tr.est_tokens(s["bytes"]),
                    "pct": round(100 * s["bytes"] / (total or 1), 1), "cut": advice, "saves_bytes": saved})
    return {"total_bytes": total, "total_tokens_approx": tr.est_tokens(total), "by_kind": kinds, "top": top,
            "duplicates": [{"line": k, "in": v} for k, v in duplicates(sources)]}


def unit(kind):
    return "description bytes" if kind == "skill" else "bytes"


def render(r) -> str:
    out = [f"always-loaded: {r['total_bytes']} bytes, ~{r['total_tokens_approx']} tokens (approximate, bytes/4), paid on every turn"]
    out += [f"  {k}: {v['sources']} source(s), {v['bytes']} {unit(k)}, ~{v['tokens_approx']} tokens, {v['pct']}%" for k, v in sorted(r["by_kind"].items())]
    out.append("top offenders:")
    for t in r["top"]:
        out.append(f"  {t['bytes']} {unit(t['kind'])} (~{t['tokens_approx']} tokens, {t['pct']}%) {t['path']}")
        out.append(f"    cut: {t['cut']}" + (f" (saves ~{t['saves_bytes']} bytes)" if t["saves_bytes"] else ""))
    if r["duplicates"]:
        out.append(f"duplicate lines across files: {len(r['duplicates'])}; keep each in one file, e.g. {r['duplicates'][0]['line'][:80]!r}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--memory-dir", action="append", default=[], type=Path)
    ap.add_argument("--skills-dir", action="append", default=[], type=Path)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--index-max", type=int, default=200)
    ap.add_argument("--section-max", type=int, default=4000)
    ap.add_argument("--desc-max", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    miss = [str(p) for p in a.paths + a.memory_dir + a.skills_dir if not p.exists()]
    notfile = [str(p) for p in a.paths if p.exists() and not p.is_file()]
    notdir = [str(p) for p in a.memory_dir + a.skills_dir if p.exists() and not p.is_dir()]
    if miss or notfile or notdir:
        print("context_audit: " + "; ".join(x for x in (miss and "not found: " + ", ".join(miss), notfile and "not a file: " + ", ".join(notfile),
                                                         notdir and "not a directory: " + ", ".join(notdir)) if x), file=sys.stderr)
        return 2
    paths = a.paths or [Path(p) for _, p, _ in tr.instruction_candidates(".") if Path(p).is_file()]
    cfg = tr.user_config_dir()  # None when no home resolves: then only the project skills are audited
    skills = a.skills_dir or [p for p in (Path(".claude/skills"), cfg and Path(cfg) / "skills") if p and p.is_dir()]
    try:
        r = audit(collect(paths, a.memory_dir, skills), a)
    except OSError as e:
        print(f"context_audit: cannot read {e.filename or e}: {e.strerror or e}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=1) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
