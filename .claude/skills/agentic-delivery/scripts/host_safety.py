#!/usr/bin/env python3
"""host_safety.py - per-host sandbox status for every agent host a project installed skills into.

Reads `templates/host-safety.tsv` (the single source of host facts) and the project tree. For each
`<host>/skills` directory present it prints one line `host-safety-<host>: <STATUS> ...`:
- `ON` / `OFF`: only where a PROJECT file proves it (`.claude` settings `sandbox.enabled`,
  `.gemini/settings.json` `tools.sandbox`). Absent or false is `OFF`; user-level config is not read.
- `COULD_NOT_CHECK`: the host has an OS sandbox but its switch is user-level or a UI setting.
- `NO_OS_SANDBOX`: no documented OS sandbox; run it in a dev container or VM (docs/host-safety.md).
Read-only; never writes or runs anything. Usage: host_safety.py [--project DIR] [--selftest]
"""
import argparse
import json
import os
import tempfile


def _json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _enabled(project, host):
    """True/False when a project file decides it, None when it cannot."""
    if host == ".claude":
        return any(_json(os.path.join(project, ".claude", f)).get("sandbox", {}).get("enabled") is True
                   for f in ("settings.json", "settings.local.json"))
    if host == ".gemini":
        return bool(_json(os.path.join(project, ".gemini", "settings.json")).get("tools", {}).get("sandbox"))
    return None


def report(project, tsv):
    out = {}
    with open(tsv, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            host, name, sandbox, _warn, url = line.rstrip("\n").split("\t")
            if not os.path.isdir(os.path.join(project, host, "skills")):
                continue
            if sandbox == "no":
                status = "NO_OS_SANDBOX: use a dev container or VM"
            else:
                on = _enabled(project, host)
                status = ("COULD_NOT_CHECK: sandbox switch is user-level or UI, not a project file" if on is None
                          else "ON" if on else "OFF: not enabled in project settings")
            out[f"host-safety-{host.lstrip('.')}"] = f"{status} ({name}; {url})"
    return out


def _selftest():
    tsv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "host-safety.tsv")
    with tempfile.TemporaryDirectory() as d:
        for h in (".claude", ".gemini", ".cursor", ".windsurf"):
            os.makedirs(os.path.join(d, h, "skills"))
        r = report(d, tsv)
        assert r["host-safety-claude"].startswith("OFF"), r
        assert r["host-safety-gemini"].startswith("OFF"), r
        assert r["host-safety-cursor"].startswith("COULD_NOT_CHECK"), r
        assert r["host-safety-windsurf"].startswith("NO_OS_SANDBOX"), r
        assert "host-safety-codex" not in r, r
        with open(os.path.join(d, ".claude", "settings.local.json"), "w") as fh:
            json.dump({"sandbox": {"enabled": True}}, fh)
        with open(os.path.join(d, ".gemini", "settings.json"), "w") as fh:
            json.dump({"tools": {"sandbox": True}}, fh)
        r = report(d, tsv)
        assert r["host-safety-claude"].startswith("ON") and r["host-safety-gemini"].startswith("ON"), r
    print("host_safety selftest ok")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=".")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    tsv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "host-safety.tsv")
    for item, status in sorted(report(args.project, tsv).items()):
        print(f"{item}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
