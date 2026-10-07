# Sourced by land_train.sh and train_land.sh: `trap clean_union_dirs EXIT` removes every LINKED worktree in
# UNION_DIRS (the merge-train scratch worktrees; each is hundreds of MB) on every exit path, errors and early
# returns included. The current worktree and the main checkout are never removed. Failures are ignored.
# union_dirs: one UNION_DIRS path per line. Newline-separated when the value holds a newline (paths may then
# contain spaces); otherwise space-separated (a path with a space needs the newline form).
union_dirs() { if [[ ${UNION_DIRS:-} == *$'\n'* ]]; then printf '%s\n' "$UNION_DIRS"; else printf '%s\n' "${UNION_DIRS:-}" | tr -s ' ' '\n'; fi; }
clean_union_dirs() {
  local d top
  top=$(git rev-parse --show-toplevel 2>/dev/null) || top=""
  while IFS= read -r d; do
    [ -d "$d" ] || continue
    [ "$(cd "$d" && pwd -P)" != "$(cd "${top:-/}" && pwd -P)" ] || continue
    [ "$(git -C "$d" rev-parse --git-common-dir 2>/dev/null)" != "$(git -C "$d" rev-parse --git-dir 2>/dev/null)" ] || continue
    git worktree remove --force "$d" >/dev/null 2>&1 || true
  done < <(union_dirs)
}
