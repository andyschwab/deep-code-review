# Sourced by train scripts. Process-table-free lock (no process-name matching, so wait chains cannot match each other):
#   lock_take <dir> [wait_secs=0] [timeout_min=30]  mkdir is the atomic claim; <dir>/pid and <dir>/ts record the holder.
#   Returns 0 (held) or 1. A held lock whose holder looks stale (pid dead, or ts older than timeout_min) is REPORTED with
#   the exact command to clear it by hand and returns 1 at once; this file never moves or deletes another owner's lock.
#   A missing or empty pid/ts means the owner is mid-write: wait like any live holder. If this shell cannot write its own
#   record it removes only what it created (its own pid file) and returns 1.
#   lock_drop <dir>  releases it (only when this shell holds it).
lock_take() {
  local d=$1 wait=${2:-0} tmo=${3:-30} p ts
  while :; do
    if mkdir "$d" 2>/dev/null; then
      { echo $$ >"$d/pid" && date +%s >"$d/ts"; } 2>/dev/null && return 0
      echo "lock: cannot write owner record in $d" >&2; lock_drop "$d"; return 1
    fi
    p=$(cat "$d/pid" 2>/dev/null); ts=$(cat "$d/ts" 2>/dev/null)
    if [[ $p =~ ^[0-9]+$ && $ts =~ ^[0-9]+$ ]]; then
      if ! kill -0 "$p" 2>/dev/null || [ $(($(date +%s) - ts)) -gt $((tmo * 60)) ]; then
        echo "STALE-LOCK $d: holder pid $p looks dead or older than ${tmo}m; not touched. If it is not yours, clear by hand: rm -f '$d/pid' '$d/ts'; rmdir '$d'" >&2
        return 1
      fi
    fi
    [ "$wait" -gt 0 ] || { echo "lock held by pid ${p:-?} ($d)" >&2; return 1; }
    wait=$((wait - 1)); sleep 1
  done
}
lock_drop() { [ "$(cat "$1/pid" 2>/dev/null)" = $$ ] && { rm -f "$1/pid" "$1/ts"; rmdir "$1" 2>/dev/null; }; return 0; }
