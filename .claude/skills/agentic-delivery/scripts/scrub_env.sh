#!/usr/bin/env bash
# scrub_env.sh [cmd args...] — run a test command without inherited git/DB env.
#
# WHY: a hook runs with GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE set; a test's `git init` then inherited
# GIT_DIR and flipped the host repo to core.bare=true. Unsets every GIT_* var plus DATABASE_URL, PG*,
# MYSQL_* and REDIS_URL (a test must never reach a real DB). With a command: exec it with those unset.
# With no command: print the `-u NAME ...` args for use as `env $(scrub_env.sh) cmd`.
args=()
for n in $(compgen -e); do
  case "$n" in GIT_*|DATABASE_URL|PG*|MYSQL_*|REDIS_URL) args+=(-u "$n") ;; esac
done
if [ $# -gt 0 ]; then exec env ${args[@]+"${args[@]}"} "$@"; fi
echo ${args[@]+"${args[@]}"}
