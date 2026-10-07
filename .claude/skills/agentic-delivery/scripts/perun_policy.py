#!/usr/bin/env python3
"""perun_policy.py — read the one resource-policy file, `.perun/policy.json`.

WHY JSON AT `.perun/policy.json`: stdlib-only (no YAML dependency), readable by bash via this CLI, and
`.perun/` is a single repo-local dir other Perun state can share. Found by walking up from the cwd, or
`$PERUN_POLICY` (an explicit path). A missing file means every default; a malformed file or bad value
fails closed (exit 2), never silently falls back.

Each dimension in DIMS takes `efficient` (default), `maximize`, `off`, or a non-negative number (a cap).
`share_learnings` takes `auto|ask|off` (default `ask`).

  perun_policy.py get <dim>      print the value (a number prints as a number)
  perun_policy.py lanes          parallel-lane count from local_cpu (see lanes())
  perun_policy.py --selftest

Exit 0 ok, 2 usage / malformed policy / unknown dimension.
"""
import json
import os
import sys
from pathlib import Path

DIMS = ("tokens", "local_cpu", "local_ram", "github_actions", "paid_api_calls", "network")
MODES = ("efficient", "maximize", "off")
SHARE = ("auto", "ask", "off")


def find_policy(start: str = ".") -> Path | None:
    """`$PERUN_POLICY`, else the nearest `.perun/policy.json` at or above `start`; None when absent."""
    if os.environ.get("PERUN_POLICY"):
        return Path(os.environ["PERUN_POLICY"])
    for d in [Path(start).resolve(), *Path(start).resolve().parents]:
        if (d / ".perun" / "policy.json").is_file():
            return d / ".perun" / "policy.json"
    return None


def load(path: Path | None = None) -> dict:
    """The validated policy with defaults filled. Raises ValueError on malformed JSON or a bad value."""
    path = path or find_policy()
    raw: dict = {}
    if path is not None and path.is_file():
        try:
            raw = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"unreadable policy {path}: {e}") from e
        if not isinstance(raw, dict):
            raise ValueError(f"policy {path} must be a JSON object")
    pol: dict = {d: "efficient" for d in DIMS} | {"share_learnings": "ask"}
    for k, v in raw.items():
        if k == "share_learnings":
            ok = v in SHARE
        elif k in DIMS:
            ok = v in MODES or (isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0)
        else:
            raise ValueError(f"unknown policy key {k!r}")
        if not ok:
            raise ValueError(f"bad value for {k}: {v!r}")
        pol[k] = v
    return pol


def lanes(mode, cores: int, load1: float | None = None) -> int:
    """Parallel heavy-lane count for a `local_cpu` value. efficient: half the cores; maximize: every idle
    core (cores minus current load1), never below 1 and never past the host's own load ceiling; off: 1
    (serial); a number: that many. host_probe.py's RAM/swap/load vetoes still apply on top."""
    if isinstance(mode, (int, float)):
        return max(1, int(mode))
    if mode == "maximize":
        return max(1, int(cores - (load1 or 0)))
    if mode == "off":
        return 1
    return max(1, cores // 2)


def main(argv: list) -> int:
    if argv[:1] == ["--selftest"]:
        return _selftest()
    try:
        pol = load()
        if argv[:1] == ["get"] and len(argv) == 2 and argv[1] in pol:
            print(pol[argv[1]])
            return 0
        if argv == ["lanes"]:
            import host_probe  # lazy: host_probe imports this module
            load1, cores = host_probe.read_load1_and_cores()
            print(lanes(pol["local_cpu"], cores or os.cpu_count() or 1, load1))
            return 0
    except ValueError as e:
        print(f"perun_policy: {e}", file=sys.stderr)
        return 2
    print(__doc__, file=sys.stderr)
    return 2


def _selftest() -> int:
    import tempfile
    d = Path(tempfile.mkdtemp())
    p = d / "policy.json"
    assert load(d / "none.json")["github_actions"] == "efficient"
    p.write_text('{"local_cpu": "maximize", "github_actions": "off", "tokens": 5000, "share_learnings": "auto"}')
    pol = load(p)
    assert (pol["local_cpu"], pol["github_actions"], pol["tokens"], pol["share_learnings"]) == ("maximize", "off", 5000, "auto")
    assert pol["network"] == "efficient"
    for bad in ('{"tokens": "lots"}', '{"nope": 1}', '{"tokens": -1}', '{"share_learnings": "yes"}', "[1]", "{"):
        p.write_text(bad)
        try:
            load(p)
        except ValueError:
            continue
        raise AssertionError(bad)
    assert [lanes(m, 8, 3) for m in ("efficient", "maximize", "off", 3)] == [4, 5, 1, 3]
    assert lanes("maximize", 8, 99) == 1
    print("perun_policy selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
