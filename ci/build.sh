#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] && [ "$(id -un)" = builder ] || { echo 'Dedicated Linux x86_64 builder account required'; exit 2; }
mode=${1:-baseline}
case "$mode" in baseline|tracking) ;; *) echo 'Invalid build mode'; exit 2;; esac
bundle=$(cd "$(dirname "$0")/.." && pwd)
base=/home/builder/y700-lineage24
inputs=/home/builder/y700-inputs
mkdir -p "$base/source" "$base/logs" "$base/candidates"
exec 9>"$base/pipeline.lock"
flock -n 9 || { echo 'Another Y700 pipeline owns the source tree'; exit 75; }
run=$(date -u +%Y%m%dT%H%M%SZ)
exec > >(tee -a "$base/logs/$run.log") 2>&1
state() { printf '{"stage":"%s","run":"%s","mode":"%s","updated_at":"%s"}\n' "$1" "$run" "$mode" "$(date -u +%FT%TZ)" > "$base/pipeline.state.tmp"; mv "$base/pipeline.state.tmp" "$base/pipeline.state"; }
trap 'rc=$?; if [ "$rc" != 0 ]; then state failed; echo "Pipeline failed: $rc; preserve this log and source tree"; fi' EXIT
state initializing
cd "$base/source"
if [ ! -d .repo ]; then
  repo init -u https://github.com/LineageOS/android.git -b lineage-24.0 --no-clone-bundle
fi
python3 "$bundle/ci/restore-reviewed-tree.py" --bundle "$bundle" --source "$PWD"
# Changes from an interrupted/previous build are never discarded automatically.
python3 "$bundle/ci/prepare-manifest.py" --bundle "$bundle" --source "$PWD" --mode "$mode"
repo init -m y700-ci.xml
state syncing
repo sync -c -j8 --retry-fetches=3 --no-clone-bundle --no-tags --fail-fast
repo manifest -r -o "$base/logs/$run-resolved.xml"
state patching
python3 "$bundle/ci/apply-reviewed-patches.py" --bundle "$bundle" --source "$PWD" --mode "$mode"
python3 "$bundle/tools/verify-webview.py" --source "$PWD"
state waiting-software-inputs
if [ ! -f "$inputs/stock-blobs.complete" ]; then
  echo 'Verified private software inputs not staged; a later dispatch can resume safely.'
  exit 76
fi
PYTHONPATH=tools/extract-utils python3 device/lenovo/asphalt/extract-files.py "$inputs/stock-blobs"
export BUILD_USERNAME=y700-builder BUILD_HOSTNAME=y700-lineage
export USE_CCACHE=1 CCACHE_DIR=/home/builder/.cache/y700-ccache
export SOONG_BUILDER_GOGC=50 SOONG_BUILDER_GOMEMLIMIT=28GiB
ccache -M 80G
source build/envsetup.sh
breakfast asphalt userdebug
state building
m -j12 bacon
state checking
out=out/target/product/asphalt
mapfile -t zips < <(find "$out" -maxdepth 1 -name 'lineage-24.0-*-asphalt.zip' -newer "$base/logs/$run-resolved.xml" -type f)
[ "${#zips[@]}" = 1 ] || { echo 'Expected exactly one new OTA'; exit 1; }
dest="$base/candidates/$run"
mkdir -p "$dest"
cp "$base/logs/$run-resolved.xml" "$dest/resolved-manifest.xml"
cp "${zips[0]}" "$dest/"
python3 "$bundle/ci/ota-feed.py" inspect "$dest/$(basename "${zips[0]}")" --output "$dest/ota-inspection.json"
sha256sum "$dest/"*.zip > "$dest/SHA256SUMS"
# No release promotion: private signing, payload/AVB validation and device acceptance remain mandatory.
state candidate-needs-acceptance
echo "Candidate retained locally: $dest"
