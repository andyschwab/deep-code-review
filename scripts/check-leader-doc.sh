#!/usr/bin/env bash
# check-leader-doc.sh [file] — every body line of docs/for-leaders.md with a digit must link to an existing
# repo file, or say "unmeasured". Headings, blank lines and numbered step markers are exempt.
# Exit 0 ok, 1 violation. `--selftest` proves it fires on a planted bad line.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
check() {
  local f=$1 dir=$2 bad=0 line l t p
  while IFS= read -r line; do
    case "$line" in '#'*|'') continue ;; esac
    l=$(sed -E 's/^[0-9]+\. //' <<<"$line")
    grep -q '[0-9]' <<<"$l" || continue
    grep -qi 'unmeasured' <<<"$l" && continue
    t=$(grep -oE '\]\([^)#]+' <<<"$l" | sed 's/^](//' || true)
    [ -n "$t" ] || { echo "no source link: $line" >&2; bad=1; continue; }
    while IFS= read -r p; do
      case "$p" in http*) continue ;; esac
      [ -e "$dir/$p" ] || { echo "dead link $p: $line" >&2; bad=1; }
    done <<<"$t"
  done <"$f"
  return $bad
}
if [ "${1:-}" = --selftest ]; then
  check <(printf -- '- Found 99%% of bugs.\n') scripts 2>/dev/null && { echo "selftest: bad line passed" >&2; exit 1; }
  check <(printf -- '- Found 99%%, [src](check-leader-doc.sh).\n- Cost: unmeasured 5.\n') scripts
  exit $?
fi
check "${1:-docs/for-leaders.md}" "$(dirname "${1:-docs/for-leaders.md}")"
