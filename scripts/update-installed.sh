#!/usr/bin/env bash
# Re-run install.sh on each TARGET with the flags recorded by its last install
# (TARGET/.claude/.dcr-install-flags), so installed skills track this checkout.
# First fetches this checkout and fast-forwards it when behind its upstream;
# refuses on a dirty tree, diverged history, or no upstream (DCR_NO_PULL=1 skips).
# Usage: scripts/update-installed.sh TARGET...
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -gt 0 ]] || { echo "usage: $0 TARGET..." >&2; exit 2; }
if [[ "${DCR_NO_PULL:-0}" != 1 ]]; then
  git -C "${HERE}" fetch -q || { echo "error: git fetch failed in ${HERE}" >&2; exit 1; }
  git -C "${HERE}" rev-parse -q --verify '@{u}' >/dev/null \
    || { echo "error: ${HERE} has no upstream branch; set one or use DCR_NO_PULL=1" >&2; exit 1; }
  if [[ "$(git -C "${HERE}" rev-parse HEAD)" != "$(git -C "${HERE}" rev-parse '@{u}')" ]]; then
    [[ -z "$(git -C "${HERE}" status --porcelain --untracked-files=no)" ]] \
      || { echo "error: ${HERE} has uncommitted changes; commit or stash, then retry" >&2; exit 1; }
    git -C "${HERE}" pull -q --ff-only \
      || { echo "error: ${HERE} cannot fast-forward (diverged from upstream); resolve manually" >&2; exit 1; }
  fi
fi
echo "dcr version: $(cat "${HERE}/.claude/skills/deep-code-review/VERSION")"
for t in "$@"; do
  m="${t}/.claude/.dcr-install-flags"
  [[ -f "${m}" ]] || { echo "error: no install marker at ${m}; run install.sh once first" >&2; exit 1; }
  flags=()
  while IFS= read -r l; do [[ -n "${l}" ]] && flags+=("${l}"); done < "${m}"
  bash "${HERE}/install.sh" ${flags[@]+"${flags[@]}"} "${t}"
done
