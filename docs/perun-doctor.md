# Perun doctor and uninstall

Installed scripts and hooks can sit in a repo and never run: an operating layer that needed an extra flag, a stale global copy, forked scripts that drifted. Nothing used to report it. Now something does.

## Check an install

```bash
python3 scripts/perun_doctor.py [REPO]          # read-only table; exit 0 = clean, 1 = something to fix
python3 scripts/perun_doctor.py [REPO] --fix    # prints the plan, replays .claude/.dcr-install-flags, re-checks
```

Run from your deep-code-review checkout (pull it first: "latest" means this checkout's version). It checks:

| Check | Meaning |
|---|---|
| installed version | repo copy vs this checkout |
| global copy | `~/.claude/skills/deep-code-review` vs this checkout (never changed by `--fix`; run `./install.sh ~` yourself) |
| hook files exist | every `.py`/`.sh` a hook command names is present |
| hooks wired | each operating-layer script (`pipe_mask_guard`, `subagent_start_inject`, `handback_cap`) is called by a hook, else "installed but never runs" |
| manual-only scripts | informational: scripts no hook, workflow, loop or other script calls |
| drifted copies | skill files, or loose copies of Perun scripts elsewhere in the repo, whose sha256 differs from the checkout |
| janitor/scheduler | a janitor or scheduler file exists, so something runs Perun without you |
| policy file | a `perun-policy` file exists |

`--fix` only re-runs `install.sh` with the recorded flags (existing skill copies move to `<host>/skill-backups/` first). It does not delete loose forks, touch the global copy, or invent a janitor or policy.

## Default-on operating layer

`./install.sh --with-delivery` (and `--full`) now applies the operating layer to `.claude/settings.local.json` by default (needs `jq`; without it the snippet is written as `.new` to merge by hand). Opt out with `--no-operating-layer`. The install prints what it changed and how to undo it.

## Uninstall

```bash
python3 scripts/perun_uninstall.py [REPO] [--dry-run]
```

Per host dir, removes each installed skill and restores the oldest pre-install backup from `skill-backups/` (a backup that is itself a Perun copy, with a `VERSION` file, is never restored). Removes exactly the operating-layer hook entries and env values from `.claude/settings.local.json`, the `.dcr-install-flags` record, and an untouched `delivery-lane.md`. It leaves `.bak` files, the `model` key and any `AGENTS.md` block alone.
