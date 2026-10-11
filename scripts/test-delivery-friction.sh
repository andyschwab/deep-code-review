#!/usr/bin/env bash
# Tests for delivery-script field friction: gh_rest.py curl fallback (macOS-sandbox TLS), fail-closed gh
# failures in land_train/train_land, lock-holder reporting, named crash causes. gh and curl are PATH stubs.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/.claude/skills/agentic-delivery/scripts"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcr-test-friction.XXXXXX")"
trap 'kill $(jobs -p) 2>/dev/null; rm -rf "$WORK"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
pass=0 fail=0
ok() { if [ "$1" -eq 0 ]; then echo "PASS  $2"; pass=$((pass + 1)); else echo "FAIL  $2"; fail=$((fail + 1)); fi; }

mkdir -p "$WORK/bin"
cat >"$WORK/bin/gh" <<'STUB'
#!/usr/bin/env bash
[ "$1 $2" = "auth token" ] && { echo stubtok; exit 0; }
[ -n "${GH_MODE:-}" ] || exit 0
case "$GH_MODE:$1" in
  tls:api|tls:pr) echo 'tls: failed to verify certificate: x509: OSStatus -26276' >&2; exit 1 ;;
  listfail:pr) [ "$2" = list ] && { echo "HTTP 502" >&2; exit 1; }
    case "$5" in headRefOid) echo "$H1" ;; baseRefName) echo main ;; isDraft) echo false ;; mergeable) echo MERGEABLE ;; headRefName) echo br1 ;; esac ;;
esac
STUB
cat >"$WORK/bin/curl" <<'STUB'
#!/usr/bin/env bash
echo "$*" >>"$CURL_LOG"; cat >>"$CURL_LOG"
n=$(grep -c "^-sS" "$CURL_LOG")
if [ "${CURL_PAGES:-}" = 1 ] && [ "$n" -eq 1 ]; then printf 'HTTP/2 200\r\nlink: <https://api.github.com/p2>; rel="next"\r\n\r\n[1]'
elif [ "${CURL_PAGES:-}" = 1 ]; then printf 'HTTP/2 200\r\n\r\n[2]'
elif [ "${CURL_404:-}" = 1 ]; then printf 'HTTP/2 404\r\n\r\n{"message":"Not Found"}'
else printf 'HTTP/2 200\r\n\r\n{"ok":true}'; fi
STUB
chmod +x "$WORK/bin/gh" "$WORK/bin/curl"; export PATH="$WORK/bin:$PATH" CURL_LOG="$WORK/curl.log"; : >"$CURL_LOG"

# --- item 4: curl fallback on the TLS error, one shared helper ---
out=$(GH_MODE=tls python3 "$SC/gh_rest.py" api repos/o/r/pulls 2>&1); rc=$?
[ $rc -eq 0 ] && [ "$out" = '{"ok":true}' ] && grep -q "Authorization: Bearer stubtok" "$CURL_LOG" && grep -q "https://api.github.com/repos/o/r/pulls" "$CURL_LOG"
ok $? "gh_rest: TLS failure on gh api retries via curl with the gh auth token"
: >"$CURL_LOG"; out=$(GH_MODE=tls CURL_PAGES=1 python3 "$SC/gh_rest.py" api --paginate repos/o/r/pulls 2>&1)
[ "$out" = "[1][2]" ]; ok $? "gh_rest: --paginate follows the Link next header; pages print back to back"
out=$(GH_MODE=tls CURL_404=1 python3 "$SC/gh_rest.py" api repos/o/r/x 2>&1); rc=$?
[ $rc -ne 0 ] && grep -q "HTTP 404" <<<"$out"; ok $? "gh_rest: a curl HTTP error fails nonzero and names the status"
: >"$CURL_LOG"; out=$(GH_MODE=tls python3 "$SC/gh_rest.py" pr view 1 2>&1); rc=$?
[ $rc -ne 0 ] && grep -q "OSStatus -26276" <<<"$out" && grep -q "no curl fallback" <<<"$out" && [ ! -s "$CURL_LOG" ]
ok $? "gh_rest: gh pr under the TLS error is not faked: fails with the cause, no curl"
out=$(GH_MODE=tls GH_TOKEN=envtok python3 -I -c "
import sys; sys.path.insert(0,'$SC'); import board_common as bc
print(bc.default_runner(['gh','api','repos/o/r'])[:2])" 2>&1)
grep -q "(0, '{\"ok\":true}')" <<<"$out"; ok $? "board_common.default_runner routes gh api through the fallback"

# --- item 2: lock holder alive/dead + age; dead holder reports the reclaim command, never auto-deletes ---
. "$SC/_lock.sh"; L="$WORK/l.lock"; sleep 60 & P=$!
mkdir "$L"; echo $P >"$L/pid"; echo $(( $(date +%s) - 90 )) >"$L/ts"
out=$(lock_take "$L" 0 30 2>&1); rc=$?
[ $rc -eq 1 ] && grep -qE "held by pid $P \(alive, age 9[0-9]s\)" <<<"$out"; ok $? "lock: busy marker reports holder alive + age"
out=$(lock_take "$L" 2 30 2>&1); [ $? -eq 1 ] && grep -q "waiting on lock held by pid $P (alive" <<<"$out"; ok $? "lock: a waiter says who it waits on (alive + age)"
kill $P; wait $P 2>/dev/null
out=$(lock_take "$L" 5 30 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "STALE-LOCK.*rm -f '$L/pid' '$L/ts'; rmdir '$L'" <<<"$out" && [ -d "$L" ]
ok $? "lock: a waiter facing a dead holder stops at once, prints the reclaim command, deletes nothing"
rm -f "$L/pid" "$L/ts"; rmdir "$L"

# --- items 1 and 3: fail closed with the cause; a crashing step is named ---
g() { git -C "$R" -c user.email=t@example.com -c user.name=T "$@"; }
git init -q --bare "$WORK/origin.git" -b main; R="$WORK/clone"; git clone -q "$WORK/origin.git" "$R" 2>/dev/null
g commit -q --allow-empty -m base; g push -q origin HEAD:main; B=$(g rev-parse HEAD)
g checkout -q -b pr1 "$B"; echo 1 >"$R/f1"; g add f1; g commit -q -m "pr 1"; export H1=$(g rev-parse pr1)
g checkout -q --detach "$B"; g merge -q --no-ff -m "merge-train: #1" pr1; U=$(g rev-parse HEAD); cd "$R" || exit 2
out=$(GH_MODE=listfail UNION_DIRS="$R" WAIT_SECS=0 LAND_CMD='echo MERGED' bash "$SC/land_train.sh" "$B" "$U" 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "could not check: stacked PRs of #1" <<<"$out" && ! grep -q MERGED <<<"$out"
ok $? "land_train: a failed gh pr list is 'could not check', not zero stacked children; nothing merged"
out=$(GH_MODE=tls UNION_DIRS="$R" WAIT_SECS=0 bash "$SC/land_train.sh" "$B" "$U" 2>&1); rc=$?
[ $rc -ne 0 ] && grep -q "land_train: failed (rc=" <<<"$out" && grep -q "pr view" <<<"$out"; ok $? "land_train: a crashing step is named (line + command), not a silent exit 1"
out=$(GH_MODE=tls VERIFY_CMD=true UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t1 1 2 2>&1); rc=$?
[ $rc -eq 1 ] && grep -q "could not check: base of #1" <<<"$out"; ok $? "train_land: gh failure reading a PR base fails closed with 'could not check'"
out=$(GH_MODE=listfail VERIFY_CMD='echo boom-cause >&2; exit 7' UNION_DIRS="$R" LOG_DIR="$WORK" bash "$SC/train_land.sh" t2 1 2 2>&1); rc=$?
[ $rc -eq 3 ] && grep -q "verify rc=7; last log line: boom-cause" <<<"$out"; ok $? "train_land: a crashing verify step names rc and its last output line"

: >"$CURL_LOG"; echo '{}' >"$WORK/body.json"; GH_MODE=tls python3 "$SC/gh_rest.py" api repos/o/r/issues --input "$WORK/body.json" >/dev/null 2>&1
grep -q -- "-X POST" "$CURL_LOG"; ok $? "gh_rest: --input without -X sends POST (matches gh api)"
grep -q "^-sS" "$CURL_LOG" && ! grep "^-sS" "$CURL_LOG" | grep -q stubtok; ok $? "gh_rest: token not in curl argv"

# --- clean_finished: lsof failure fails closed ---
CF="$WORK/cf"; mkdir -p "$CF"; git init -q "$CF/main" -b main; git -C "$CF/main" commit -q --allow-empty -m i
git -C "$CF/main" worktree add -q -b done1 "$CF/wts/done1"
printf '#!/usr/bin/env bash\necho "lsof: WARNING: can not read" >&2; exit 1\n' >"$WORK/bin/lsof"; chmod +x "$WORK/bin/lsof"
printf '#!/usr/bin/env bash\necho "MERGED abc"\n' >"$WORK/gh2"; chmod +x "$WORK/gh2"
out=$(cd "$CF/main" && ROOT="$CF/wts" GH="$WORK/gh2" bash "$SC/clean_finished.sh" 2>&1)
[ -d "$CF/wts/done1" ] && grep -q "could not check" <<<"$out" && grep -q "removed=0 skipped=1" <<<"$out"; ok $? "clean_finished: lsof error skips removal and says why"
rm -f "$WORK/bin/lsof"

echo "$pass passed, $fail failed"; [ "$fail" -eq 0 ]
