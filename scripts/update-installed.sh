#!/usr/bin/env bash
# Re-run install.sh on each TARGET with the flags recorded by its last install
# (TARGET/.claude/.dcr-install-flags), so installed skills track this checkout.
# Usage: scripts/update-installed.sh TARGET...   (git pull this repo first)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -gt 0 ]] || { echo "usage: $0 TARGET..." >&2; exit 2; }
for t in "$@"; do
  m="${t}/.claude/.dcr-install-flags"
  [[ -f "${m}" ]] || { echo "error: no install marker at ${m}; run install.sh once first" >&2; exit 1; }
  flags=()
  while IFS= read -r l; do [[ -n "${l}" ]] && flags+=("${l}"); done < "${m}"
  bash "${HERE}/install.sh" ${flags[@]+"${flags[@]}"} "${t}"
done
