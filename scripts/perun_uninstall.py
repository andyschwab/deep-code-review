#!/usr/bin/env python3
"""perun uninstall: undo install.sh in a target repo, using only what the install marker recorded.

Usage: python3 scripts/perun_uninstall.py [REPO] [--apply]

Default is a dry run: it prints the full plan and changes nothing. `--apply` performs it.
Source of truth is REPO/.claude/.perun-install.json (written by install.sh). Without it
nothing is removed (re-run install.sh once to write it).

Plan, built and validated before anything is touched:
  * settings.local.json is parsed first; invalid JSON aborts with no change. Only hook
    entries, env values and sandbox/permissions values recorded in the marker (and still
    equal to the recorded value) are removed, and the "model" key only if Perun set it.
    The file itself goes if install created it and nothing else is left. Temp file + rename.
  * Skill dirs: only files whose sha256 still equals the recorded install hash are removed.
    Files you added or edited are kept and listed; the dir stays if any are kept. When a
    dir is fully removed, the oldest pre-install backup (no VERSION file) is restored.
  * skill-backups dirs install created: removed file by file when unchanged. A pre-install
    original is removed only after it was restored; otherwise it is kept and listed.
  * Slash commands, house-defaults.md and settings .bak.<ts> files: removed only if install
    wrote them and they are unchanged.
  * delivery-lane.md is removed only if Perun created it and it is unchanged.
  * AGENTS.md: the blocks install wrote are cut out; the file goes if install created it and nothing else is left.
Every delete is one file at a time, only for paths in the marker, each checked to resolve inside REPO
(never rm -rf on a computed path). Only __pycache__/*.pyc under a removed skill dir are removed without being listed.
Emptied directories are removed last (rmdir, never recursive). Stdlib only.
"""
import argparse, json, os, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perun_marker  # noqa: E402

SRC = Path(__file__).resolve().parent.parent


def inside(repo, rel):
    """True when repo/rel resolves (symlinked parents followed) to a path under repo, and rel is not absolute."""
    root = os.path.realpath(repo)
    real = os.path.join(os.path.realpath((repo / rel).parent), (repo / rel).name)
    return not os.path.isabs(rel) and os.path.commonpath([root, real]) == root


def rmf(repo, rel):
    """Unlink one marker-listed file, after re-checking it is inside repo."""
    if not inside(repo, rel):
        raise ValueError(f"refusing to delete {rel}: outside {repo}")
    (repo / rel).unlink(missing_ok=True)


def strip(c, tree):
    """Inverse of perun_marker.added: drop the recorded values from settings dict c; containers it empties go too. Returns count."""
    n = 0
    for k, v in tree.items():
        if k not in c:
            continue
        before = n
        if isinstance(v, dict) and isinstance(c[k], dict):
            n += strip(c[k], v)
        elif isinstance(v, list) and isinstance(c[k], list):
            keep = [x for x in c[k] if x not in v]
            n += len(c[k]) - len(keep)
            c[k] = keep
        elif c[k] == v:
            del c[k]
            n += 1
            continue
        if n > before and c[k] in ({}, []):
            del c[k]
    return n


def prune_empty(repo, rels):
    """rmdir (never recursive) each path and its parents up to, not including, repo while they are empty."""
    for rel in rels:
        p = repo / rel
        while p != repo and p.is_relative_to(repo):
            try:
                p.rmdir()
            except FileNotFoundError:
                pass
            except OSError:
                break
            p = p.parent


def plan(repo):
    """Return (ops, notes). ops = list of (description, callable). Raises ValueError before any change."""
    m = perun_marker.load(repo)
    if m is None:
        raise ValueError("no .claude/.perun-install.json marker: nothing is safe to remove (re-run install.sh to write one)")
    ops, notes = [], []
    rels = [*m.get("skills", {}), *m.get("backups", {}), *m.get("files", {})]
    rels += [d + "/" + f for g in ("skills", "backups") for d, fs in m.get(g, {}).items() for f in fs]
    if m.get("agent"):
        rels.append(m["agent"]["path"])
    bad = [r for r in rels if not inside(repo, r)]
    if bad:
        raise ValueError(f"marker lists paths outside {repo} ({bad[0]}); nothing changed")
    cfg = repo / ".claude/settings.local.json"
    if cfg.is_file() and (m.get("hooks") or m.get("env") or m.get("model") or m.get("settings") or m.get("settings_created")):
        try:
            c = json.loads(cfg.read_text())
        except ValueError as e:
            raise ValueError(f"{cfg} is not valid JSON ({e}); fix it first, nothing changed")
        n = 0
        for item in m.get("hooks", []):
            have = c.get("hooks", {}).get(item["event"], [])
            if item["entry"] in have:
                have.remove(item["entry"]); n += 1
                if not have:
                    del c["hooks"][item["event"]]
        if "hooks" in c and not c["hooks"]:
            del c["hooks"]
        envn = 0
        for k, v in m.get("env", {}).items():
            if c.get("env", {}).get(k) == v:
                del c["env"][k]; envn += 1
        if "env" in c and not c["env"]:
            del c["env"]
        model = bool(m.get("model")) and c.get("model") == m["model"]
        if model:
            del c["model"]
        sn = strip(c, m.get("settings", {}))

        def write(c=c):
            if not c and m.get("settings_created"):
                cfg.unlink()
                return
            tmp = cfg.with_name(cfg.name + ".perun-tmp")
            tmp.write_text(json.dumps(c, indent=2) + "\n")
            os.replace(tmp, cfg)
        ops.append((f"settings.local.json: remove {n} hook entr{'y' if n == 1 else 'ies'}, {envn} env value(s), {sn} sandbox/permissions value(s)" + (", model pin" if model else ""), write))
    restored = set()
    for d, files in sorted(m.get("skills", {}).items()):
        dest = repo / d
        if not dest.is_dir():
            continue
        keep = [str(p.relative_to(dest)) for p in sorted(dest.rglob("*")) if p.is_file()
                and "__pycache__" not in p.parts and files.get(str(p.relative_to(dest))) != perun_marker.sha(p)]
        gone = [r for r in files if (dest / r).is_file() and r not in keep]

        def rm(dest=dest, gone=gone, d=d):
            for r in gone:
                rmf(repo, f"{d}/{r}")
            for pyc in sorted(dest.rglob("__pycache__/*.pyc")):  # bytecode a skill run left behind: not in the marker, so not listed
                rmf(repo, str(pyc.relative_to(repo)))
            for dp, _, _ in sorted(os.walk(dest), reverse=True):
                if not any(Path(dp).iterdir()):
                    Path(dp).rmdir()
        ops.append((f"{d}: remove {len(gone)} installed file(s)" + (f"; KEEP {len(keep)} added/edited: {', '.join(keep[:5])}" if keep else ""), rm))
        host, _, name = d.partition("/skills/")
        orig = sorted(b for b in (repo / host / "skill-backups").glob(name + "-*") if b.is_dir() and not (b / "VERSION").exists())
        if orig and not keep:
            restored.add(str(orig[0].relative_to(repo)))
            ops.append((f"{d}: restore {orig[0].relative_to(repo)}", lambda b=orig[0], dest=dest: shutil.copytree(b, dest)))
        elif keep:
            notes.append(f"{d}: kept files, so the pre-install backup was not restored (see {host}/skill-backups)")
    for d, files in sorted(m.get("backups", {}).items()):
        if not (repo / d).is_dir():
            continue
        if not (repo / d / "VERSION").exists() and d not in restored:
            notes.append(f"{d}: pre-install original kept (its skill dir was not restored)")
            continue
        have = [r for r in files if (repo / d / r).is_file()]
        gone = [r for r in have if perun_marker.sha(repo / d / r) == files[r]]

        def rmb(d=d, gone=gone):
            for r in gone:
                rmf(repo, f"{d}/{r}")
            for dp, _, _ in sorted(os.walk(repo / d), reverse=True):
                if not any(Path(dp).iterdir()):
                    Path(dp).rmdir()
        ops.append((f"{d}: remove {len(gone)} backup file(s)", rmb))
        if len(gone) < len(have):
            notes.append(f"{d}: kept {len(have) - len(gone)} backup file(s) you changed")
    for f, h in sorted(m.get("files", {}).items()):
        if (repo / f).is_file() and perun_marker.sha(repo / f) == h:
            ops.append((f"remove {f}", lambda f=f: rmf(repo, f)))
    a = m.get("agent")
    if a and (repo / a["path"]).is_file() and perun_marker.sha(repo / a["path"]) == a["sha"]:
        ops.append((f"remove {a['path']}", lambda a=a: rmf(repo, a["path"])))
    am, ag = m.get("agents_md"), repo / "AGENTS.md"
    if am and ag.is_file():
        text = new = ag.read_text()
        for b in am["blocks"]:
            new = re.sub(rf"\n?^<!-- {re.escape(b)}:begin -->\n.*?^<!-- {re.escape(b)}:end -->\n?", "", new, flags=re.S | re.M)
        if new != text:
            whole = am["created"] and new.strip() == "# AGENTS.md"

            def cut(new=new, whole=whole):
                ag.unlink() if whole else ag.write_text(new)
            ops.append((f"AGENTS.md: remove {len(am['blocks'])} Perun block(s)" + (" (and the file, install created it)" if whole else ""), cut))
    return ops, notes


def finish(repo, m):
    for f in (".claude/.dcr-install-flags", ".claude/.dcr-install-flags.local", perun_marker.MARKER):
        rmf(repo, f)
    prune_empty(repo, [*m.get("skills", {}), *(d.partition("/skills/")[0] + "/skill-backups" for d in m.get("skills", {})), *m.get("backups", {}), *m.get("files", {}), ".claude/agents", ".claude"])


def run(repo, apply=False):
    """Print the plan; apply it only when apply=True. Returns the list of plan lines."""
    ops, notes = plan(repo)
    lines = [d for d, _ in ops] + notes
    if apply:
        m = perun_marker.load(repo)
        for _, fn in ops:
            fn()
        finish(repo, m)
    return lines


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--apply", action="store_true", help="perform the plan (default: print it only)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    if repo == SRC:
        sys.exit("error: target is the checkout itself")
    try:
        out = run(repo, a.apply)
    except ValueError as e:
        sys.exit(f"error: {e}")
    print("\n".join(("" if a.apply else "would: ") + l for l in out) or "nothing to undo")
    if not a.apply:
        print("dry run: nothing changed; re-run with --apply to do it")
