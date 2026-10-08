# Sourced by train scripts. Process-table-free lock (no process-name matching, so wait chains cannot match each other):
#   lock_take <dir> [timeout_min=30] [wait_secs=0]  mkdir is the atomic claim; <dir>/pid and <dir>/ts record the holder.
#   Returns 0 (held), 1 (held by a live holder after the wait, or the owner record could not be written).
#   A missing, empty or non-numeric pid/ts counts as YOUNG (the owner may be mid-write) and is never reclaimed. An old
#   lock (ts older than timeout_min) whose pid is dead is moved aside to <dir>.stale.$$ (mv: one reclaimer wins), its
#   record is re-read, and it is deleted only if it is still old and dead; otherwise it is moved back (or reported).
#   An old lock whose pid is alive is reported, NEVER deleted. Holder = the calling shell ($$).
#   lock_drop <dir>  releases it (only when this shell holds it).
lock_take() {
  local d=$1 tmo=${2:-30} wait=${3:-0} p ts now s
  while :; do
    if mkdir "$d" 2>/dev/null; then
      { echo $$ >"$d/pid" && date +%s >"$d/ts"; } 2>/dev/null || { rm -f "$d/pid" "$d/ts"; rmdir "$d" 2>/dev/null; echo "lock: cannot write owner record in $d" >&2; return 1; }
      return 0
    fi
    now=$(date +%s)
    if _lock_stale "$d" "$tmo" "$now"; then
      p=$(cat "$d/pid")
      s="$d.stale.$$"
      if mv "$d" "$s" 2>/dev/null; then
        if _lock_stale "$s" "$tmo" "$now"; then
          echo "STALE-LOCK $d: older than ${tmo}m, holder '$(cat "$s/pid")' dead; reclaimed" >&2
          rm -f "$s/pid" "$s/ts"; rmdir "$s" 2>/dev/null || true; continue
        fi
        mv "$s" "$d" 2>/dev/null || echo "STALE-LOCK $d: record changed during reclaim; left at $s" >&2
      fi
    elif _lock_old "$d" "$tmo" "$now"; then
      echo "STALE-LOCK $d: older than ${tmo}m but pid $(cat "$d/pid") is alive; not deleted" >&2
    fi
    [ "$wait" -gt 0 ] || { echo "lock held by pid $(cat "$d/pid" 2>/dev/null || echo '?') ($d)" >&2; return 1; }
    wait=$((wait - 1)); sleep 1
  done
}
# _lock_old: well-formed numeric pid and ts, and ts older than the timeout. _lock_stale: that, and the pid is dead.
_lock_old() {
  local p ts
  p=$(cat "$1/pid" 2>/dev/null); ts=$(cat "$1/ts" 2>/dev/null)
  case $p$ts in ''|*[!0-9]*) return 1 ;; esac
  [ -n "$p" ] && [ -n "$ts" ] && [ $(($3 - ts)) -gt $(($2 * 60)) ]
}
_lock_stale() { _lock_old "$@" && ! kill -0 "$(cat "$1/pid")" 2>/dev/null; }
lock_drop() { [ "$(cat "$1/pid" 2>/dev/null)" = $$ ] && { rm -f "$1/pid" "$1/ts"; rmdir "$1" 2>/dev/null; }; return 0; }
