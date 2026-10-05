#!/usr/bin/env bash
# reap_own.sh — kill your own dev servers older than MAX_AGE_S whose cwd is under ROOT (your own lane or
# session tree). Never kills by name alone: a process must be owned by the current user AND have its cwd
# under ROOT, so other lanes' and other users' servers are untouchable. Safe to run on every tick.
#
# Env: ROOT (required, absolute dir), PATTERN (pgrep -f regex, default 'next-server|next dev'),
# KEEP (optional dir under ROOT whose servers are spared), MAX_AGE_S (default 10800).
# Prints "reaped=N".
set -euo pipefail
: "${ROOT:?set ROOT to your own tree}"
ROOT=$(cd "$ROOT" && pwd -P)  # lsof reports resolved paths; a symlinked ROOT would match nothing
KEEP=${KEEP:+$(cd "$KEEP" && pwd -P)}; PATTERN=${PATTERN:-next-server|next dev}; KEEP=${KEEP:-}; MAX=${MAX_AGE_S:-10800}
n=0
for P in $(pgrep -u "$(id -u)" -f "$PATTERN" || true); do
  C=$(lsof -a -p "$P" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
  case "$C" in
    "$ROOT"|"$ROOT"/*) ;;
    *) continue ;;
  esac
  if [ -n "$KEEP" ]; then case "$C" in "${KEEP%/}"|"${KEEP%/}"/*) continue ;; esac; fi
  E=$(ps -o etime= -p "$P" | tr -d ' ' | awk -F'[-:]' '{n=NF; s=$n+60*$(n-1); if(n>=3)s+=3600*$(n-2); if(n>=4)s+=86400*$(n-3); print s}')
  if [ "${E:-0}" -gt "$MAX" ]; then kill "$P" && n=$((n+1)); fi
done
echo "reaped=$n"
