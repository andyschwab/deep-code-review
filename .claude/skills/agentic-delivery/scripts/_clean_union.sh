# Sourced by land_train.sh and train_land.sh: `trap clean_union_dirs EXIT` removes every LINKED worktree in
# UNION_DIRS (the merge-train scratch worktrees; each is hundreds of MB) on every exit path, errors and early
# returns included. The current worktree and the main checkout are never removed. Failures are ignored.
clean_union_dirs() {
  local d top
  top=$(git rev-parse --show-toplevel 2>/dev/null) || top=""
  for d in ${UNION_DIRS:-}; do
    [ -d "$d" ] || continue
    [ "$(cd "$d" && pwd -P)" != "$(cd "${top:-/}" && pwd -P)" ] || continue
    [ "$(git -C "$d" rev-parse --git-common-dir 2>/dev/null)" != "$(git -C "$d" rev-parse --git-dir 2>/dev/null)" ] || continue
    git worktree remove --force "$d" >/dev/null 2>&1 || true
  done
}
