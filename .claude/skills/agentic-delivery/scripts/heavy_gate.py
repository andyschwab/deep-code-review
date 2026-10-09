#!/usr/bin/env python3
"""heavy_gate.py — PreToolUse(Bash) hook: defer a heavy local command while the machine is busy.

WHY: host_probe.py and the heavy-lease primitive in perun_policy.py existed but nothing called
them, so fleets ran 10+ test runners at once (load1 > 3x cores, swap climbing, OOM kills). This
hook runs on every Bash call, so the admission check happens without anyone remembering it.

What it does: if the command starts a test runner or a build (DEFAULT_PATTERNS, or the
newline-separated regexes in $PERUN_HEAVY_PATTERNS, each matched at the start of a shell segment, after runner wrappers are stripped),
it denies the call when host_probe.decide(lane_type="heavy") says HOLD (load1 > cores or low free
RAM; swap is not read, one sample shows no trend) or when the machine-wide heavy leases already fill the
slot count (perun_policy.heavy_slots; local_cpu=maximize raises it to every core). Otherwise it
prints nothing and the call proceeds. While a train gate holds the EXCLUSIVE lease (perun_policy.py heavy-exclusive) every heavy command is denied with "gate running: wait". It never takes a lease and never stops or deletes anything.

Fail open: any error inside the hook (bad stdin, unreadable host data, an unparsable command line, a bad policy) allows the call.
A block is a JSON `permissionDecision: "deny"` on stdout with exit 0, never exit 2, so a crash
cannot turn into a block. Register it as `python3 ".../heavy_gate.py" || true`.

Fast path (<200ms): one os.getloadavg(), one memory_pressure or /proc/meminfo read, one swap read
(no two-sample trend, no `top`). Test injection: PERUN_GATE_LOAD1, PERUN_GATE_CORES,
PERUN_GATE_FREE_RAM_PCT override the readings; PERUN_HEAVY_DIR points the lease dir at a fixture.
"""
import json
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PATTERNS = (
    r"(python3? -m )?pytest\b", r"(npx |pnpm |yarn )?(jest|vitest|playwright)\b",
    r"(npm|pnpm|yarn|bun) (run )?test\b", r"cargo (test|nextest)\b", r"go test\b",
    r"(npx )?next build\b", r"(npm|pnpm|yarn|bun) run build\b", r"(npx )?tsc -b\b",
)
PUNCT = ";()<>|&\n"
WRAP = re.compile(r"(\w+=\S*|env|time|nice|command|exec|sudo|npx|uv run|poetry run|pipx run|pnpm exec|python[\d.]* -m)$")
LIGHT_FLAGS = {"--version", "--help", "-h", "--collect-only", "--co"}


def _segments(command: str):
    """Token lists, one per shell segment. Quotes and heredoc bodies never split; raises ValueError on a parse error."""
    lines, delim = [], None
    for line in command.split("\n"):
        if delim is not None:
            delim = None if line.strip() == delim else delim
            continue
        m = re.search(r"<<-?\s*(['\"]?)(\w+)\1", line)
        delim = m.group(2) if m else None
        lines.append(line)
    lex = shlex.shlex("\n".join(lines), posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    seg, out = [], []
    for tok in lex:
        if set(tok) <= set(PUNCT):
            out.append(seg)
            seg = []
        else:
            seg.append(tok)
    return out + [seg]


def _strip_wrappers(toks):
    """Drop leading runner wrappers (env/VAR=x/time/sudo, npx, uv|poetry|pipx run, pnpm exec, python -m) and their flags."""
    while toks:
        two = " ".join(toks[:2])
        if WRAP.match(two) and len(toks) > 1:
            toks = toks[2:]
        elif WRAP.match(toks[0]):
            toks = toks[1:]
        else:
            break
        while toks and toks[0].startswith("-"):
            toks = toks[1:]
    return toks


def is_heavy(command: str, patterns) -> bool:
    """True when a shell segment of `command` begins, after runner wrappers, with a heavy pattern.
    Quote- and heredoc-aware: `git commit -m "fix; pytest"` is not heavy; `cd x && uv run pytest` is.
    Light invocations (--version, --help, --collect-only, `playwright install`) are never heavy.
    A command that does not parse (unclosed quote) is NOT heavy: the gate fails open."""
    try:
        segs = _segments(command or "")
    except ValueError:
        return False
    for toks in segs:
        toks = _strip_wrappers(toks)
        if not toks or LIGHT_FLAGS & set(toks) or (toks[0] == "playwright" and (toks[1:2] or [""])[0].startswith("install")):
            continue
        seg = " ".join(toks)
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
    if perun_policy.exclusive_holder(perun_policy.lease_dir()):
        return "HOLD gate running: wait", load1, cores, ram
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
