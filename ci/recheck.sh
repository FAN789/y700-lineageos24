#!/usr/bin/env bash
set -euo pipefail
[ "$(id -un)" = builder ] || exit 2
run=${1:-}
[[ "$run" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || { echo 'Invalid candidate identifier'; exit 2; }
base=/home/builder/y700-lineage24
bundle=$(cd "$(dirname "$0")/.." && pwd)
exec 9>"$base/pipeline.lock"
flock -n 9 || { echo 'Source pipeline active; no concurrent validation'; exit 75; }
dest="$base/candidates/$run"
[ -d "$dest" ] && [ ! -L "$dest" ] || exit 2
mapfile -t zips < <(find "$dest" -maxdepth 1 -type f -name 'lineage-24.0-*-asphalt.zip')
[ "${#zips[@]}" = 1 ] || { echo 'Exactly one candidate OTA required'; exit 2; }
python3 "$bundle/ci/ota-feed.py" inspect "${zips[0]}" --output "$dest/ota-inspection.json.next"
mv "$dest/ota-inspection.json.next" "$dest/ota-inspection.json"
(cd "$dest"; sha256sum "$(basename "${zips[0]}")" > SHA256SUMS)
printf '{"candidate_run":"%s","transport_integrity":"passed","release_accepted":false,"ci_revision":"%s"}\n' "$run" "$(git -C "$bundle" rev-parse HEAD)" > "$dest/verification.state"
echo 'Existing OTA CRC, full hash, payload/metadata hashes and streaming offsets passed; release acceptance still pending.'
cat "$dest/SHA256SUMS"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  cat "$dest/verification.state" >> "$GITHUB_STEP_SUMMARY"
  echo 'This job validates an existing artifact; it does not rebuild, sign, promote or flash it.' >> "$GITHUB_STEP_SUMMARY"
fi
