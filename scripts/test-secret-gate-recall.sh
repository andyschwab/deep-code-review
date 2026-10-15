#!/usr/bin/env bash
#
# Regression: the committed .banlist.txt must catch the common secret shapes
# (recall) without flagging placeholders or look-alike identifiers (precision).
# Every value is FAKE and assembled from fragments at runtime so this file
# never matches the banlist itself.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATES="$ROOT/scripts/ci-gates.sh"
W="$(mktemp -d "${TMPDIR:-/tmp}/dcr-secret-recall.XXXXXX")"
trap 'rm -rf "$W"' EXIT
cp "$ROOT/.banlist.txt" "$W/.banlist.txt"   # committed list only, no local list
mkdir "$W/hit" "$W/ok"

A="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"   # 36 filler chars
B="Qx9Lm2Zt7Vb4Nc8Kd3Hf6Jw1Rs5Yp0Gu"       # 34 mixed chars
hit() { printf '%s\n' "$2" >"$W/hit/$1.txt"; }
ok()  { printf '%s\n' "$2" >"$W/ok/$1.txt"; }

hit aws_akia   "id=AKIA""ZZZZZZZZZZZZZZZZ"
hit aws_asia   "id=ASIA""ZZZZZZZZZZZZZZZZ"
hit gh_pat     "t=gh""p_${A}"
hit gh_fine    "t=github""_pat_${B}_abcdefghij"
hit slack_hook "u=https://hooks.slack"".com/services/T0ABCDEFGH/B0ABCDEFGH/${B:0:24}"
hit slack_bot  "t=xox""b-1234567890-abcdefghij"
hit stripe     "k=sk""_live_${B:0:24}"
hit aiza       "k=AI""za${B}ABC"
hit openai     "k=sk""-${B:0:24}"
hit generic    "api_key = \"${B}Ab\""
hit pem_rsa    "-----BEGIN RSA PRIVATE ""KEY-----"
hit pem_pkcs8  "-----BEGIN PRIVATE ""KEY-----"
hit pgp        "-----BEGIN PGP PRIVATE KEY"" BLOCK-----"
hit phone      "call +1 (415) 555""-0173 now"
hit ssn        "ssn: 078-05""-1120"

ok gh_x_placeholder  "t=gh""p_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ok risk_identifier   ".risk-managementdashboardcomponent { color: red }"
ok slack_placeholder "u=https://hooks.slack.com/services/T000/B000/XXXX"
ok public_key        "-----BEGIN PUBLIC KEY-----"
ok cert              "-----BEGIN CERTIFICATE-----"
ok example_email     "mail jane@example.com"
ok short_phone       "call 555-0100"
ok git_sha           "commit dae90ae5375db76d048a2c14aca07d1604ea9241"
ok env_ref           "token = os.environ[\"X\"]"
ok version           "version = \"1.511.0\""

fail=0
for f in "$W"/hit/*.txt; do
  if bash "$GATES" privacy --banlist "$W/.banlist.txt" "$f" >/dev/null 2>&1; then
    echo "FAIL  missed: $(basename "$f")"; fail=1
  fi
done
for f in "$W"/ok/*.txt; do
  if ! bash "$GATES" privacy --banlist "$W/.banlist.txt" "$f" >/dev/null 2>&1; then
    echo "FAIL  false positive: $(basename "$f")"; fail=1
  fi
done
[ "$fail" -eq 0 ] && echo "PASS  secret gate recall/precision"
exit "$fail"
