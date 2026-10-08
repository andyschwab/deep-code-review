#!/usr/bin/env python3
"""heavy_gate.py — PreToolUse(Bash) hook: defer a heavy local command while the machine is busy.

WHY: host_probe.py and the heavy-lease primitive in perun_policy.py existed but nothing called
them, so fleets ran 10+ test runners at once (load1 > 3x cores, swap climbing, OOM kills). This
hook runs on every Bash call, so the admission check happens without anyone remembering it.

What it does: if the command starts a test runner or a build (DEFAULT_PATTERNS, or the
newline-separated regexes in $PERUN_HEAVY_PATTERNS, each matched at the start of a shell segment),
it denies the call when host_probe.decide(lane_type="heavy") says HOLD (load1 > cores, low free
RAM, swap climbing past the policy floor) or when the machine-wide heavy leases already fill the
slot count (perun_policy.heavy_slots; local_cpu=maximize raises it to every core). Otherwise it
prints nothing and the call proceeds. It never takes a lease and never stops or deletes anything.

Fail open: any error inside the hook (bad stdin, unreadable host data, bad policy) allows the call.
A block is a JSON `permissionDecision: "deny"` on stdout with exit 0, never exit 2, so a crash
cannot turn into a block. Register it as `python3 ".../heavy_gate.py" || true`.

Fast path (<200ms): one os.getloadavg(), one memory_pressure or /proc/meminfo read, one swap read
(no two-sample trend, no `top`). Test injection: PERUN_GATE_LOAD1, PERUN_GATE_CORES,
PERUN_GATE_FREE_RAM_PCT override the readings; PERUN_HEAVY_DIR points the lease dir at a fixture.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PATTERNS = (
    r"(python3? -m )?pytest\b", r"(npx |pnpm |yarn )?(jest|vitest|playwright)\b",
    r"(npm|pnpm|yarn|bun) (run )?test\b", r"cargo (test|nextest)\b", r"go test\b",
    r"(npx )?next build\b", r"(npm|pnpm|yarn|bun) run build\b", r"(npx )?tsc -b\b",
)
SEGMENT = re.compile(r"&&|\|\||[;|&\n]")
PREFIX = re.compile(r"^(\s*(\w+=\S*|env|time|nice|command|exec|sudo)\s+)*")


def is_heavy(command: str, patterns) -> bool:
    """True when any shell segment of `command` begins with a heavy pattern.
    Edge: `git commit -m "fix pytest"` and `grep jest` do not match; `cd x && npm test` does."""
    for seg in SEGMENT.split(command or ""):
        seg = PREFIX.sub("", seg.strip().lstrip("("))
        if any(re.match(p, seg) for p in patterns):
            return True
    return False


def _float_env(name):
    v = os.environ.get(name)
    return float(v) if v not in (None, "") else None


def verdict(policy_cpu="efficient") -> tuple:
    """`(block_reason_or_None, load1, cores, free_ram_pct)` from fast readings."""
    import host_probe
    import perun_policy
    load1 = _float_env("PERUN_GATE_LOAD1")
    if load1 is None:
        load1 = os.getloadavg()[0]
    cores = int(_float_env("PERUN_GATE_CORES") or os.cpu_count() or 1)
    ram = _float_env("PERUN_GATE_FREE_RAM_PCT")
    if ram is None:
        ram = host_probe.read_free_ram_pct()
    swap = 0.0  # one sample cannot show a trend; (0, 0) keeps decide() reading load and RAM
    v = host_probe.decide(swap_samples=(swap, swap), free_ram_pct=ram, lane_type="heavy",
                          load1=load1, cores=cores)
    if v.startswith("HOLD"):
        return v, load1, cores, ram
    slots = perun_policy.heavy_slots(cores, load1)
    if policy_cpu == "maximize":
        slots = max(slots, cores)
    held = len(perun_policy.active_leases(perun_policy.lease_dir()))
    if held >= slots:
        return f"HOLD heavy-lease-full {held}/{slots}", load1, cores, ram
    return None, load1, cores, ram


def main() -> int:
    try:
        data = json.load(sys.stdin)
        cmd = (data.get("tool_input") or {}).get("command", "")
        env_pat = os.environ.get("PERUN_HEAVY_PATTERNS")
        patterns = [p for p in env_pat.splitlines() if p.strip()] if env_pat else DEFAULT_PATTERNS
        if not is_heavy(cmd, patterns):
            return 0
        import perun_policy
        try:
            cpu = perun_policy.load().get("local_cpu", "efficient")
        except ValueError:
            cpu = "efficient"
        reason, load1, cores, ram = verdict(cpu)
        if not reason:
            return 0
        ram_s = f"{ram:.0f}% free" if ram is not None else "unknown"
        msg = (f"machine busy (load {load1:.1f}/{cores} cores, RAM {ram_s}; {reason}): "
               "wait and retry, or run a narrower test (one file or -k filter)")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": msg}}))
    except Exception:  # fail open: the gate must never block work because the gate broke
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
