#!/usr/bin/env python3
"""perun uninstall: undo install.sh in a target repo.

Usage: python3 scripts/perun_uninstall.py [REPO] [--dry-run]

For each skill this checkout ships, in every host dir (.claude/.cursor/.agents/.codex):
removes the installed copy and restores the OLDEST backup under <host>/skill-backups/
that is not itself a Perun copy (no VERSION file), i.e. what you had before install.
Removes exactly the operating-layer hook entries (and env values) that match the template
from .claude/settings.local.json, plus .claude/.dcr-install-flags and an untouched
.claude/agents/delivery-lane.md. Leaves .bak files, the "model" key, AGENTS.md blocks and
backups of Perun copies in place. Stdlib only.
"""
import argparse, json, shutil, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
TEMPLATE = SRC / ".claude/skills/agentic-delivery/templates/operating-layer.settings.json"
HOSTS = (".claude", ".cursor", ".agents", ".codex")


def run(repo, dry=False):
    log = []

    def do(msg, fn):
        log.append(msg)
        if not dry:
            fn()

    for host in HOSTS:
        for sk in sorted(p.name for p in (SRC / ".claude/skills").iterdir() if (p / "SKILL.md").is_file()):
            dest = repo / host / "skills" / sk
            if not dest.is_dir():
                continue
            do(f"remove {dest.relative_to(repo)}", lambda d=dest: shutil.rmtree(d))
            origs = sorted(b for b in (repo / host / "skill-backups").glob(sk + "-*") if b.is_dir() and not (b / "VERSION").exists())
            if origs:
                do(f"restore {origs[0].relative_to(repo)} -> {dest.relative_to(repo)}", lambda b=origs[0], d=dest: shutil.copytree(b, d))
    cfg = repo / ".claude/settings.local.json"
    if cfg.is_file() and TEMPLATE.is_file():
        t, c = json.loads(TEMPLATE.read_text()), json.loads(cfg.read_text())
        n = 0
        for ev, entries in t.get("hooks", {}).items():
            have = c.get("hooks", {}).get(ev, [])
            keep = [e for e in have if e not in entries]
            n += len(have) - len(keep)
            if keep:
                c["hooks"][ev] = keep
            elif ev in c.get("hooks", {}):
                del c["hooks"][ev]
        if not c.get("hooks", True):
            del c["hooks"]
        for k, v in t.get("env", {}).items():
            if c.get("env", {}).get(k) == v:
                del c["env"][k]
        if "env" in c and not c["env"]:
            del c["env"]
        do(f"remove {n} operating-layer hook entr{'y' if n == 1 else 'ies'} from {cfg.relative_to(repo)}", lambda: cfg.write_text(json.dumps(c, indent=2) + "\n"))
    agent = repo / ".claude/agents/delivery-lane.md"
    if agent.is_file() and "Default delivery lane for bounded implementation work" in agent.read_text():
        do(f"remove {agent.relative_to(repo)}", agent.unlink)
    flags = repo / ".claude/.dcr-install-flags"
    if flags.is_file():
        do(f"remove {flags.relative_to(repo)}", flags.unlink)
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    if repo == SRC:
        sys.exit("error: target is the checkout itself")
    for line in run(repo, a.dry_run) or ["nothing to undo"]:
        print(("would " if a.dry_run else "") + line)
