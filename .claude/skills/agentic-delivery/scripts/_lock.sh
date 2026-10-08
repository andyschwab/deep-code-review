# Sourced by train scripts. Process-table-free lock (no process-name matching, so wait chains cannot match each other):
#   lock_take <dir> [timeout_min=30] [wait_secs=0]  mkdir is the atomic claim; <dir>/pid and <dir>/ts record the holder.
#   Returns 0 (held), 1 (held by a live holder after the wait). A lock older than timeout_min whose pid is dead is moved
#   aside atomically (mv; one reclaimer wins) and reported. An old lock whose pid is alive, or a young one, is NEVER
#   taken: it prints "STALE-LOCK ... not deleted" (or "lock held") and waits/fails. Holder = the calling shell ($$).
#   lock_drop <dir>  releases it (only when this shell holds it).
lock_take() {
  local d=$1 tmo=${2:-30} wait=${3:-0} p ts now
  while :; do
    if mkdir "$d" 2>/dev/null; then echo $$ >"$d/pid"; date +%s >"$d/ts"; return 0; fi
    p=$(cat "$d/pid" 2>/dev/null || true); ts=$(cat "$d/ts" 2>/dev/null || echo 0); now=$(date +%s)
    if [ $((now - ts)) -gt $((tmo * 60)) ]; then
      if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then echo "STALE-LOCK $d: older than ${tmo}m but pid $p is alive; not deleted" >&2
      elif mv "$d" "$d.stale.$$" 2>/dev/null; then
        echo "STALE-LOCK $d: older than ${tmo}m, holder '${p:-?}' dead; reclaimed" >&2
        rm -f "$d.stale.$$/pid" "$d.stale.$$/ts"; rmdir "$d.stale.$$" 2>/dev/null || true; continue
      fi
    fi
    [ "$wait" -gt 0 ] || { echo "lock held by pid ${p:-?} ($d)" >&2; return 1; }
    wait=$((wait - 1)); sleep 1
  done
}
lock_drop() { [ "$(cat "$1/pid" 2>/dev/null)" = $$ ] && { rm -f "$1/pid" "$1/ts"; rmdir "$1" 2>/dev/null; }; return 0; }
