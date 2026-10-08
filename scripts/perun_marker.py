#!/usr/bin/env python3
"""Install marker: what install.sh itself added to a repo, so uninstall removes only that.

Usage (called by install.sh): perun_marker.py TARGET --dirs REL... [--pre FILE --template FILE] [--agent-created] [--files REL...] [--version V] [--remote URL]

Writes TARGET/.claude/.perun-install.json, merged with any previous marker:
  skills: {<host>/skills/<name>: {<file>: sha256}}  hashes of the copy just installed
  hooks:  [{event, entry}]  operating-layer entries absent before this install
  env:    {key: value}      env keys absent before this install
  model:  "sonnet" | null   set only when the settings had no "model" before
  files:  {<rel>: sha256}  slash commands install wrote fresh (never pre-existing files)
  agent:  {path, sha} | null  delivery-lane.md when install created it
  version, remote             the installed release and where it came from (perun_auto_update.py)
Stdlib only.
"""
import argparse, hashlib, json, sys
from pathlib import Path

MARKER = ".claude/.perun-install.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hash_dir(d):
    return {str(p.relative_to(d)): sha(p) for p in sorted(Path(d).rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def load(target):
    f = Path(target) / MARKER
    return json.loads(f.read_text()) if f.is_file() else None


def record(target, dirs, pre=None, template=None, agent_created=False, files=(), version=None, remote=None):
    target = Path(target)
    m = load(target) or {}
    m.update({k: v for k, v in (("version", version), ("remote", remote)) if v})
    m.setdefault("skills", {}).update({d: hash_dir(target / d) for d in dirs if (target / d).is_dir()})
    m.setdefault("hooks", []); m.setdefault("env", {}); m.setdefault("model", None); m.setdefault("agent", None)
    cfg = target / ".claude/settings.local.json"
    if pre and template and cfg.is_file():
        before, now, t = (json.loads(Path(x).read_text()) for x in (pre, cfg, template))
        for ev, entries in t.get("hooks", {}).items():
            for e in entries:
                if "<" in (e.get("matcher") or ""):
                    continue
                item = {"event": ev, "entry": e}
                if e not in before.get("hooks", {}).get(ev, []) and e in now.get("hooks", {}).get(ev, []) and item not in m["hooks"]:
                    m["hooks"].append(item)
        for k, v in t.get("env", {}).items():
            if k not in before.get("env", {}) and now.get("env", {}).get(k) == v:
                m["env"][k] = v
        if "model" not in before and now.get("model") == "sonnet":
            m["model"] = "sonnet"
    m.setdefault("files", {}).update({f: sha(target / f) for f in files if (target / f).is_file()})
    agent = target / ".claude/agents/delivery-lane.md"
    if agent_created and agent.is_file():
        m["agent"] = {"path": ".claude/agents/delivery-lane.md", "sha": sha(agent)}
    out = target / MARKER
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2) + "\n")
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--dirs", nargs="*", default=[])
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--pre")
    ap.add_argument("--template")
    ap.add_argument("--agent-created", action="store_true")
    ap.add_argument("--version")
    ap.add_argument("--remote")
    a = ap.parse_args()
    record(a.target, a.dirs, a.pre, a.template, a.agent_created, a.files, a.version, a.remote)
