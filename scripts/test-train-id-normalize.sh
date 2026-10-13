#!/usr/bin/env bash
# Contract: a test id emitted with trailing whitespace or CRLF still matches its clean form everywhere train_flake.sh /
# train_land.sh compare ids (one normalizer: `train_flake.sh --norm`). Stubs only; writes under $WORK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-train-norm.XXXXXX")"
trap '[ -n "$WORK" ] && rm -r "$WORK" 2>/dev/null' EXIT
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

printf 'a b \r\n c\t\n' | bash "$SC/train_flake.sh" --norm >"$WORK/n"; [ "$(cat "$WORK/n")" = "$(printf 'a b\n c')" ]; ok $? "--norm strips trailing space/CR/tab only (inner and leading kept)"

# --base: runner prints the id with a trailing space + CR; the clean id must still be proven failing there (exit 0 = pre-existing)
export RERUN_CMD='printf "FAIL t1 \r\n"; exit 1'
bash "$SC/train_flake.sh" --base 't1' >/dev/null 2>&1; ok $? "--base: id emitted with trailing space+CRLF matches clean id"
bash "$SC/train_flake.sh" --base 't1 ' >/dev/null 2>&1; ok $? "--base: id passed with trailing space matches clean emit"
bash "$SC/train_flake.sh" --base 't2' >/dev/null 2>&1; [ $? -eq 1 ]; ok $? "--base: a different id is still not matched (exit 1)"

# list mode: failed id has trailing space+CR, baseline lists it clean -> skipped, no REAL
printf 't1 \r\n' >"$WORK/fails"; : >"$WORK/base0"
hdr="# baseline host=$(hostname -s) inv=$(printf %s inv | { shasum -a 256 2>/dev/null || sha256sum; } | cut -c1-16)"
printf '%s\nt1\n' "$hdr" >"$WORK/base"
out=$(FLAKE_INVOCATION=inv RERUN_CMD=false bash "$SC/train_flake.sh" "$WORK/fails" "$WORK/base" 2>&1); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ]; ok $? "list: trailing-space failed id matches clean baseline id (skipped, not blamed)"
printf '%s\r\nt1 \r\n' "$hdr" >"$WORK/base"; printf 't1\n' >"$WORK/fails"
out=$(FLAKE_INVOCATION=inv RERUN_CMD=false bash "$SC/train_flake.sh" "$WORK/fails" "$WORK/base" 2>&1); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ]; ok $? "list: CRLF baseline (header and id) matches clean failed id"
printf 't1 \r\n' >"$WORK/fails"
out=$(RERUN_CMD=false bash "$SC/train_flake.sh" "$WORK/fails" 2>/dev/null); [ "$out" = "REAL t1" ]; ok $? "list: REAL id is printed normalized (no trailing space)"
echo "id-normalize: $pass passed, $fail failed"; [ "$fail" -eq 0 ]
