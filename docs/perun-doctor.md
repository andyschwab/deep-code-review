# Perun doctor and uninstall

Installed scripts and hooks can sit in a repo and never run: an operating layer that needed an extra flag, a stale global copy, forked scripts that drifted. Nothing used to report it. Now something does.

## Check an install

```bash
python3 scripts/perun_doctor.py [REPO]          # read-only table; exit 0 = clean, 1 = something to fix
python3 scripts/perun_doctor.py [REPO] --fix    # prints the plan, asks you to type yes (or pass --yes), replays flags, re-checks
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

`--fix` prints the plan and what the default-on operating layer would add to your settings, then needs a typed `yes` on a terminal (or `--yes`, which prints a warning). It exits non-zero if the reinstall fails. It only re-runs `install.sh` with the recorded flags (existing skill copies move to `<host>/skill-backups/` first). It does not delete loose forks, touch the global copy, or invent a janitor or policy.

## Default-on operating layer

`./install.sh --with-delivery` (and `--full`) now applies the operating layer to `.claude/settings.local.json` by default (needs `jq`; without it the snippet is written as `.new` to merge by hand). Opt out with `--no-operating-layer`. The install prints what it changed and how to undo it.

## Uninstall

```bash
python3 scripts/perun_uninstall.py [REPO]            # dry run: prints the plan, changes nothing
python3 scripts/perun_uninstall.py [REPO] --apply    # does it
```

It trusts only `.claude/.perun-install.json`, written by `install.sh` (no marker: nothing is removed; re-run `install.sh` once). Settings are parsed first; invalid JSON aborts with no change, and the file is replaced by temp file plus rename. It removes only the hook entries and env values the marker recorded, and the `model` key only if Perun set it. Skill files are removed only if their sha256 still matches the install; files you added or edited stay and are listed, and the pre-install backup in `skill-backups/` is restored only when the whole dir was removed. It leaves `.bak.<timestamp>` files and any `AGENTS.md` block alone.

## Releases and tags

`scripts/land-release.sh` stamps the release and never tags. After the release commit is on origin/main, run `scripts/land-release.sh tag` from a checkout at that commit: it creates and pushes the annotated `vX.Y.Z`, skips a tag that already exists locally, and refuses if origin/main is not at your version.
