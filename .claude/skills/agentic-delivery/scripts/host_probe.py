#!/usr/bin/env python3
"""host_probe.py — the fan-out spawn/hold predicate, computed once, not
re-derived from prose each session.

WHY THIS EXISTS
---------------
`fanout-host-sizing.md` **Gate on free RAM and the swap trend** documents the
predicate in prose; different sessions re-derived it differently (one gated
on `load1` alone, which that section explicitly warns against), and a memory
gate can read healthy — free RAM >40%, swap flat — while contention is
actually disk/CPU-bound: gates measured running 5-10x slower under ~25
concurrent heavy lanes despite a green memory reading. This script is the one
mechanized form of the predicate: it prints exactly one line, `SPAWN`,
`HOLD <reason,...>`, or `COULD_NOT_CHECK <what>`, and a `COULD_NOT_CHECK`
never authorizes a spawn, same as a `HOLD`.

THE PREDICATE (`decide()`, pure — every branch below is `fanout-host-sizing.md`'s own)
---------------------------------------------------------------------------------------
In order, first hit wins:
1. **Swap trend, primary.** Two samples a beat apart; unreadable is
   `COULD_NOT_CHECK swap`; climbing (second > first) is `HOLD swap-trend` —
   checked before free RAM so a swap-trend hold is never misread as a RAM
   problem, and it fires **even with high free RAM** (a post-mitigation
   number that reads healthiest exactly as a thrash collapses delivery).
2. **Free RAM, a veto only, never a licence.** Below `FREE_RAM_HOLD_PCT`
   (~15%) is `HOLD low-ram`; healthy RAM does not itself return `SPAWN` —
   every later check still runs.
3. **Free disk vs. the measured per-lane footprint** (`--per-lane-disk-bytes`,
   only when given): `disk_free < per_lane_bytes * (live_lanes + 1)` is
   `HOLD disk`. `live_lanes` doubles as the worktree count — this delivery
   model is one worktree per heavy lane (`fanout-host-sizing.md`,
   "Worktree-per-lane is the right isolation").
4. **The paired load+CPU-idle brake, `--lane-type cpu` only.** `load1` past
   core count *together with* CPU idle collapsing toward zero is a
   CPU-contention signature disk-I/O-wait cannot fake; `load1` alone never
   holds, and never for a non-`cpu` lane type (I/O-bound and light lanes tax
   neither).
5. **The gate-latency canary, regardless of what memory says.** Times a
   fixed cheap gate (`--canary CMD`) against its recorded idle baseline
   (`--baseline-file`); above `CANARY_HOLD_RATIO` (~2x) is `HOLD canary`; a
   missing/unreadable baseline is `COULD_NOT_CHECK canary`.
6. **The live-lane cap** (`--live-lanes`/`--max-lanes`, only when both given):
   at or over the cap is `HOLD lane-cap`.
7. Otherwise `SPAWN`.

USAGE
-----
  host_probe.py --lane-type {cpu,io,light} [--canary CMD --baseline-file F]
                [--live-lanes N --max-lanes N] [--per-lane-disk-bytes N]
                [--sample-interval SECONDS]
  host_probe.py --selftest
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

FREE_RAM_HOLD_PCT = 15.0        # fanout-host-sizing.md's ~15% working-buffer floor
CANARY_HOLD_RATIO = 2.0         # fanout-host-sizing.md's "roughly 2x baseline"
CPU_CONTENTION_IDLE_PCT = 10.0  # "CPU idle collapsing toward zero"

EXIT = {"SPAWN": 0, "HOLD": 1, "COULD_NOT_CHECK": 2}


def decide(*, swap_samples: tuple, free_ram_pct: float | None, lane_type: str,
           load1: float | None = None, cores: int | None = None, cpu_idle_pct: float | None = None,
           free_disk_bytes: int | None = None, per_lane_disk_bytes: int | None = None,
           live_lanes: int | None = None, max_lanes: int | None = None,
           canary_requested: bool = False, canary_ratio: float | None = None) -> str:
    """One verdict: `SPAWN`, `HOLD <reason,...>`, or `COULD_NOT_CHECK <what>` — see module doc."""
    s1, s2 = swap_samples
    if s1 is None or s2 is None:
        return "COULD_NOT_CHECK swap"
    if s2 > s1:
        return "HOLD swap-trend"
    if free_ram_pct is None:
        return "COULD_NOT_CHECK ram"
    if free_ram_pct < FREE_RAM_HOLD_PCT:
        return "HOLD low-ram"
    if per_lane_disk_bytes is not None:
        if free_disk_bytes is None:
            return "COULD_NOT_CHECK disk"
        if free_disk_bytes < per_lane_disk_bytes * ((live_lanes or 0) + 1):
            return "HOLD disk"
    if lane_type == "cpu" and load1 is not None and cores:
        if load1 > cores and cpu_idle_pct is not None and cpu_idle_pct < CPU_CONTENTION_IDLE_PCT:
            return "HOLD cpu-contention"
    if canary_requested:
        if canary_ratio is None:
            return "COULD_NOT_CHECK canary"
        if canary_ratio > CANARY_HOLD_RATIO:
            return "HOLD canary"
    if max_lanes is not None and live_lanes is not None and live_lanes >= max_lanes:
        return "HOLD lane-cap"
    return "SPAWN"


def exit_code(verdict: str) -> int:
    """The process exit code for one `decide()` verdict string."""
    return EXIT[verdict.split(" ", 1)[0]]


# ---------------------------------------------------------------------------
# OS readers — macOS and Linux, stdlib plus the platform's own text tools.
# Any unreadable value is None, never guessed; each is independently testable.
# ---------------------------------------------------------------------------
def _run(cmd: list) -> str | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def read_swap_used_mb() -> float | None:
    """Swap used, in MB; `sysctl vm.swapusage` (macOS) or `/proc/meminfo` (Linux)."""
    if sys.platform == "darwin":
        out = _run(["sysctl", "vm.swapusage"])
        m = out and re.search(r"used\s*=\s*([\d.]+)M", out)
        return float(m.group(1)) if m else None
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            info = dict(re.findall(r"^(\S+):\s*(\d+)", fh.read(), re.MULTILINE))
        total, free = info.get("SwapTotal"), info.get("SwapFree")
        return (int(total) - int(free)) / 1024 if total and free else None
    except OSError:
        return None


def read_free_ram_pct() -> float | None:
    """Free RAM as a percentage; `memory_pressure` (macOS) or `/proc/meminfo` (Linux)."""
    if sys.platform == "darwin":
        out = _run(["memory_pressure"])
        m = out and re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
        return float(m.group(1)) if m else None
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            info = dict(re.findall(r"^(\S+):\s*(\d+)", fh.read(), re.MULTILINE))
        total, avail = info.get("MemTotal"), info.get("MemAvailable")
        return 100.0 * int(avail) / int(total) if total and avail else None
    except OSError:
        return None


def read_load1_and_cores() -> tuple:
    """`(load1, core_count)`; `sysctl -n vm.loadavg` (macOS) or `/proc/loadavg` (Linux)."""
    cores = os.cpu_count()
    if sys.platform == "darwin":
        out = _run(["sysctl", "-n", "vm.loadavg"])
        m = out and re.search(r"\{\s*([\d.]+)", out)
        return (float(m.group(1)) if m else None), cores
    try:
        with open("/proc/loadavg", encoding="utf-8") as fh:
            return float(fh.read().split()[0]), cores
    except (OSError, ValueError, IndexError):
        return None, cores


def read_cpu_idle_pct(sample_interval: float = 0.3) -> float | None:
    """CPU idle percentage; `top -l 1 -n 0` (macOS) or a short `/proc/stat` delta (Linux)."""
    if sys.platform == "darwin":
        out = _run(["top", "-l", "1", "-n", "0"])
        m = out and re.search(r"([\d.]+)%\s*idle", out)
        return float(m.group(1)) if m else None
    try:
        def snap():
            with open("/proc/stat", encoding="utf-8") as fh:
                return [int(x) for x in fh.readline().split()[1:]]
        a = snap()
        time.sleep(sample_interval)
        b = snap()
        deltas = [y - x for x, y in zip(a, b)]
        total = sum(deltas)
        return 100.0 * deltas[3] / total if total and len(deltas) > 3 else None
    except (OSError, ValueError, IndexError):
        return None


def read_free_disk_bytes(path: str = ".") -> int | None:
    """Free bytes on `path`'s filesystem (`shutil.disk_usage`, cross-platform stdlib)."""
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return None


def run_canary(cmd: str, baseline_file: str) -> tuple:
    """`(elapsed_seconds, ratio)` for one `--canary` run vs. its recorded idle baseline.

    `(None, None)` when the baseline file is missing, unreadable, non-numeric,
    or <= 0, or the canary command itself cannot run — never a guessed ratio.
    """
    try:
        with open(baseline_file, encoding="utf-8") as fh:
            baseline = float(fh.read().strip())
    except (OSError, ValueError):
        return None, None
    if baseline <= 0:
        return None, None
    start = time.monotonic()
    try:
        subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None, None
    elapsed = time.monotonic() - start
    return elapsed, elapsed / baseline


def probe(lane_type: str, canary_cmd: str | None = None, baseline_file: str | None = None,
          sample_interval: float = 1.0, live_lanes: int | None = None, max_lanes: int | None = None,
          per_lane_disk_bytes: int | None = None) -> str:
    """The real, host-reading invocation: samples swap twice `sample_interval` seconds
    apart, reads the rest of the predicate's inputs, runs the canary if given, and
    returns one `decide()` verdict."""
    s1 = read_swap_used_mb()
    time.sleep(sample_interval)
    s2 = read_swap_used_mb()
    load1, cores = read_load1_and_cores()
    canary_ratio = None
    if canary_cmd and baseline_file:
        _, canary_ratio = run_canary(canary_cmd, baseline_file)
    return decide(
        swap_samples=(s1, s2), free_ram_pct=read_free_ram_pct(), lane_type=lane_type,
        load1=load1, cores=cores, cpu_idle_pct=read_cpu_idle_pct(),
        free_disk_bytes=read_free_disk_bytes(), per_lane_disk_bytes=per_lane_disk_bytes,
        live_lanes=live_lanes, max_lanes=max_lanes,
        canary_requested=bool(canary_cmd), canary_ratio=canary_ratio,
    )


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute the fan-out spawn/hold predicate once.")
    parser.add_argument("--lane-type", choices=("cpu", "io", "light"), default="light",
                        help="cpu enables the paired load+CPU-idle contention brake")
    parser.add_argument("--canary", help="a fixed cheap gate command timed against --baseline-file")
    parser.add_argument("--baseline-file", help="recorded idle-run elapsed seconds for --canary")
    parser.add_argument("--sample-interval", type=float, default=1.0,
                        help="seconds between the two swap samples (the trend 'beat')")
    parser.add_argument("--live-lanes", type=int, help="caller's own count of running heavy lanes")
    parser.add_argument("--max-lanes", type=int, help="caller's own concurrency ceiling")
    parser.add_argument("--per-lane-disk-bytes", type=int, help="measured disk footprint of one heavy lane")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.canary and not args.baseline_file:
        parser.error("--canary needs --baseline-file")
    verdict = probe(args.lane_type, args.canary, args.baseline_file, args.sample_interval,
                    args.live_lanes, args.max_lanes, args.per_lane_disk_bytes)
    print(verdict)
    return exit_code(verdict)


# ---------------------------------------------------------------------------
# --selftest — decide() is pure and takes injected readings directly, so every
# branch is exercised with no OS calls and no sleeping.
# ---------------------------------------------------------------------------
def _selftest() -> int:
    passed = 0
    failed = 0

    def case(name, got, want):
        nonlocal passed, failed
        if got == want:
            passed += 1
            print(f"PASS  {name}")
        else:
            failed += 1
            print(f"FAIL  {name} (got {got!r}, want {want!r})")

    case("all-healthy-spawns", decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light"), "SPAWN")
    case("swap-unreadable-could-not-check",
         decide(swap_samples=(None, 100), free_ram_pct=50, lane_type="light"), "COULD_NOT_CHECK swap")
    case("swap-climbing-holds-even-with-high-free-ram",
         decide(swap_samples=(100, 200), free_ram_pct=90, lane_type="light"), "HOLD swap-trend")
    case("canary-over-ratio-holds-regardless-of-memory",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                canary_requested=True, canary_ratio=6.0), "HOLD canary")
    case("canary-under-ratio-spawns",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                canary_requested=True, canary_ratio=1.1), "SPAWN")
    case("canary-missing-baseline-could-not-check",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                canary_requested=True, canary_ratio=None), "COULD_NOT_CHECK canary")
    case("low-ram-holds", decide(swap_samples=(100, 100), free_ram_pct=10, lane_type="light"), "HOLD low-ram")
    case("ram-unreadable-could-not-check",
         decide(swap_samples=(100, 100), free_ram_pct=None, lane_type="light"), "COULD_NOT_CHECK ram")
    case("disk-insufficient-holds",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                free_disk_bytes=1_000, per_lane_disk_bytes=2_000, live_lanes=0), "HOLD disk")
    case("disk-sufficient-spawns",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                free_disk_bytes=10_000, per_lane_disk_bytes=2_000, live_lanes=1), "SPAWN")
    case("disk-half-given-could-not-check",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                free_disk_bytes=None, per_lane_disk_bytes=2_000), "COULD_NOT_CHECK disk")
    case("cpu-contention-holds-for-cpu-lane",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="cpu",
                load1=20.0, cores=8, cpu_idle_pct=2.0), "HOLD cpu-contention")
    case("high-load-alone-never-holds-non-cpu-lane",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                load1=20.0, cores=8, cpu_idle_pct=2.0), "SPAWN")
    case("high-load-healthy-idle-never-holds-cpu-lane",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="cpu",
                load1=20.0, cores=8, cpu_idle_pct=81.0), "SPAWN")
    case("lane-cap-holds",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light",
                live_lanes=10, max_lanes=10), "HOLD lane-cap")
    case("lane-cap-not-given-never-holds",
         decide(swap_samples=(100, 100), free_ram_pct=50, lane_type="light", live_lanes=999), "SPAWN")
    case("spawn-exit-zero", exit_code("SPAWN"), 0)
    case("hold-exit-nonzero", exit_code("HOLD swap-trend") != 0, True)
    case("could-not-check-exit-nonzero", exit_code("COULD_NOT_CHECK swap") != 0, True)

    import tempfile
    tmp = tempfile.mkdtemp(prefix="host-probe-selftest-")
    try:
        baseline = os.path.join(tmp, "baseline.txt")
        with open(baseline, "w", encoding="utf-8") as fh:
            fh.write("0.001")
        elapsed, ratio = run_canary("true", baseline)
        case("canary-real-run-has-elapsed-and-ratio",
             elapsed is not None and ratio is not None and ratio > 0, True)
        case("canary-missing-baseline-file-none",
             run_canary("true", os.path.join(tmp, "missing.txt")), (None, None))
        with open(baseline, "w", encoding="utf-8") as fh:
            fh.write("not-a-number")
        case("canary-malformed-baseline-none", run_canary("true", baseline), (None, None))

        verdict = probe("light", sample_interval=0.05)
        case("probe-end-to-end-returns-valid-verdict",
             verdict.split(" ", 1)[0] in ("SPAWN", "HOLD", "COULD_NOT_CHECK"), True)
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)

    print(f"\nselftest: {passed}/{passed + failed} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
