#!/usr/bin/env python3
"""Install marker: what install.sh itself added to a repo, so uninstall removes only that.

Usage (called by install.sh): perun_marker.py TARGET --dirs REL... [--pre FILE --template FILE] [--agent-created] [--files REL...] [--backups REL...] [--agents-block NAME...] [--agents-created] [--settings-created] [--version V] [--remote URL]
       perun_marker.py prune BACKUP_ROOT NAME NEW DEST   (keep only the newest Perun backup of a skill)

Writes TARGET/.claude/.perun-install.json, merged with any previous marker:
  skills: {<host>/skills/<name>: {<file>: sha256}}  hashes of the copy just installed
  hooks:  [{event, entry}]  operating-layer entries absent before this install
  env:    {key: value}      env keys absent before this install
  model:  "sonnet" | null   set only when the settings had no "model" before
  files:  {<rel>: sha256}  slash commands, house-defaults.md and settings .bak files install wrote fresh (never pre-existing files)
  backups: {<rel dir>: {<file>: sha256}}  skill-backups dirs this install created (still on disk)
  settings: {sandbox, permissions}  only the values the operating layer added (nested; lists hold the added items)
  settings_created: true when install created settings.local.json
  agents_md: {blocks: [name], created: bool}  AGENTS.md blocks install wrote, and whether it created the file
  agent:  {path, sha} | null  delivery-lane.md when install created it
  version, remote             the installed release and where it came from (perun_auto_update.py)
Stdlib only.
"""
import argparse, hashlib, json, os, re, sys
from pathlib import Path

MARKER = ".claude/.perun-install.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hash_dir(d):
    return {str(p.relative_to(d)): sha(p) for p in sorted(Path(d).rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def load(target):
    f = Path(target) / MARKER
    return json.loads(f.read_text()) if f.is_file() else None


def added(have, tpl):
    """What template `tpl` contributes that `have` lacks: dicts recurse, lists keep missing items, an existing scalar wins."""
    if isinstance(tpl, dict):
        out = {k: a for k, v in tpl.items() if (a := added(have.get(k) if isinstance(have, dict) else None, v)) not in (None, {}, [])}
        return out
    if isinstance(tpl, list):
        return [x for x in tpl if x not in (have if isinstance(have, list) else [])]
    return tpl if have is None else None


def merge(a, b):
    """Union of two `added` trees (marker memory across re-runs)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: merge(a.get(k), b.get(k)) if k in a and k in b else a.get(k, b.get(k)) for k in {**a, **b}}
    if isinstance(a, list) and isinstance(b, list):
        return a + [x for x in b if x not in a]
    return b


def _rm_tree(d):
    """Delete a directory file by file (symlinks unlinked, never followed), then its dirs bottom-up."""
    for dp, dn, fn in os.walk(d, topdown=False):
        for n in fn + dn:
            if (Path(dp) / n).is_symlink() or (Path(dp) / n).is_file():
                (Path(dp) / n).unlink()
        os.rmdir(dp)


def prune_backups(root, name, new, dest):
    """Keep one Perun backup per skill: drop `new` when identical to `dest`, else drop older ones that carry a VERSION file.
    Pre-Perun originals (no VERSION file) and anything not named <name>-<timestamp> are never touched. Returns a status line."""
    root, new = Path(root), Path(new)
    if (new / "VERSION").is_file() and hash_dir(new) == hash_dir(dest):
        _rm_tree(new)
        return "backup: identical to the installed copy, not kept"
    pat = re.compile(re.escape(name) + r"-\d{8}-\d{6}(-\d+)?$")
    old = [b for b in root.iterdir() if b != new and pat.match(b.name) and b.is_dir() and not b.is_symlink() and (b / "VERSION").is_file()]
    for b in old:
        _rm_tree(b)
    return f"backup: kept the latest only ({len(old)} older Perun backup(s) removed)" if (new / "VERSION").is_file() else "backup: pre-Perun original kept"


def record(target, dirs, pre=None, template=None, agent_created=False, files=(), version=None, remote=None, backups=(), agents_blocks=(), agents_created=False, settings_created=False):
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
        for k in ("sandbox", "permissions"):
            if k in t and (a := added(before.get(k), t[k])):
                m.setdefault("settings", {})[k] = merge(m.get("settings", {}).get(k, {}), a)
    if settings_created:
        m["settings_created"] = True
    if agents_blocks:
        am = m.setdefault("agents_md", {"blocks": [], "created": False})
        am["blocks"] += [b for b in agents_blocks if b not in am["blocks"]]
        am["created"] = am["created"] or agents_created
    m.setdefault("backups", {}).update({d: hash_dir(target / d) for d in backups if (target / d).is_dir()})
    m["backups"] = {d: h for d, h in m["backups"].items() if (target / d).is_dir()}
    m.setdefault("files", {}).update({f: sha(target / f) for f in files if (target / f).is_file()})
    agent = target / ".claude/agents/delivery-lane.md"
    if agent_created and agent.is_file():
        m["agent"] = {"path": ".claude/agents/delivery-lane.md", "sha": sha(agent)}
    out = target / MARKER
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2) + "\n")
    return m


if __name__ == "__main__":
    if sys.argv[1:2] == ["prune"]:
        print(prune_backups(*sys.argv[2:6]))
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--dirs", nargs="*", default=[])
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--pre")
    ap.add_argument("--template")
    ap.add_argument("--agent-created", action="store_true")
    ap.add_argument("--backups", nargs="*", default=[])
    ap.add_argument("--agents-block", nargs="*", default=[])
    ap.add_argument("--agents-created", action="store_true")
    ap.add_argument("--settings-created", action="store_true")
    ap.add_argument("--version")
    ap.add_argument("--remote")
    a = ap.parse_args()
    record(a.target, a.dirs, a.pre, a.template, a.agent_created, a.files, a.version, a.remote, a.backups, a.agents_block, a.agents_created, a.settings_created)
