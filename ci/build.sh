#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] && [ "$(id -un)" = builder ] || { echo 'Dedicated Linux x86_64 builder account required'; exit 2; }
mode=${1:-baseline}
case "$mode" in baseline|tracking) ;; *) echo 'Invalid build mode'; exit 2;; esac
bundle=$(cd "$(dirname "$0")/.." && pwd)
source "$bundle/ci/resource-profile.sh"
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
repo sync -c -j"$Y700_SYNC_JOBS" --retry-fetches=3 --no-clone-bundle --no-tags --fail-fast
repo manifest -r -o "$base/logs/$run-resolved.xml"
state patching
python3 "$bundle/ci/check-sandbox.py" --source "$PWD"
python3 "$bundle/ci/apply-reviewed-patches.py" --bundle "$bundle" --source "$PWD" --mode "$mode"
python3 "$bundle/ci/check-ucsi-typec3.py" --source "$PWD"
python3 "$bundle/ci/check-recovery-adsp.py" --source "$PWD"
python3 "$bundle/ci/check-native-ethernet.py" --source "$PWD"
python3 "$bundle/ci/check-dual-network.py" --source "$PWD"
python3 "$bundle/ci/test-dual-network.py" --source "$PWD"
python3 "$bundle/ci/check-preservation.py" --source "$PWD"
python3 "$bundle/ci/test-preservation.py" --source "$PWD"
python3 "$bundle/ci/test-postinstall-routing.py" --source "$PWD"
python3 "$bundle/tools/verify-webview.py" --source "$PWD"
state waiting-software-inputs
if [ ! -f "$inputs/stock-blobs.complete" ]; then
  echo 'Verified private software inputs not staged; a later dispatch can resume safely.'
  exit 76
fi
PYTHONPATH=tools/extract-utils python3 device/lenovo/asphalt/extract-files.py "$inputs/stock-blobs"
export BUILD_USERNAME=y700-builder BUILD_HOSTNAME=y700-lineage
export USE_CCACHE=1 CCACHE_DIR=/home/builder/.cache/y700-ccache
export GOCACHE=/home/builder/.cache/go-build
mkdir -p "$GOCACHE"
[ -w "$GOCACHE" ] || { echo 'Go build cache is not writable by builder'; exit 1; }
export SOONG_BUILDER_GOGC=50 SOONG_BUILDER_GOMEMLIMIT="$Y700_GO_MEMORY_LIMIT"
printf 'Build profile: jobs=%s sync_jobs=%s Go=%s ccache=%s\n' "$Y700_BUILD_JOBS" "$Y700_SYNC_JOBS" "$Y700_GO_MEMORY_LIMIT" "$Y700_CCACHE_MAXSIZE"
ccache -M "$Y700_CCACHE_MAXSIZE"
source build/envsetup.sh
breakfast asphalt userdebug
state building
m -j"$Y700_BUILD_JOBS" bacon
if grep -Fq 'Build sandboxing disabled due to nsjail error.' "$base/logs/$run.log"; then
  echo 'Rejecting build: Soong reported a failed native sandbox.'
  exit 1
fi
state checking
out=out/target/product/asphalt
ota=$(python3 "$bundle/ci/select-ota.py" --product-out "$out" --newer-than "$base/logs/$run-resolved.xml")
zips=("$ota")
[ "${#zips[@]}" = 1 ] || { echo 'Expected exactly one new OTA'; exit 1; }
dest="$base/candidates/$run"
mkdir -p "$dest"
cp "$base/logs/$run-resolved.xml" "$dest/resolved-manifest.xml"
cp "${zips[0]}" "$dest/"
python3 "$bundle/ci/ota-feed.py" inspect "$dest/$(basename "${zips[0]}")" --output "$dest/ota-inspection.json"
python3 "$bundle/ci/check-preservation.py" --source "$PWD" --candidate "$dest"
python3 "$bundle/ci/validate-native.py" --source "$PWD" --candidate "$dest" --pipeline-lock-fd 9
python3 "$bundle/ci/check-kernel-preservation.py" --source "$PWD" --candidate "$dest"
python3 "$bundle/ci/check-ucsi-typec3.py" --source "$PWD" --candidate "$dest" --target-files "$out/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files" --previous-target-files /home/builder/y700-usbfix-20261028/signed/target-files
recovery_baseline=$(python3 "$bundle/ci/review-recovery-baseline.py" --source "$PWD" --target-files "$out/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files" --previous-target-files /home/builder/y700-ucsi-typec3-20261028/signed/target-files --output "$dest/reviewed-recovery-baseline")
python3 "$bundle/ci/check-recovery-adsp.py" --source "$PWD" --candidate "$dest" --target-files "$out/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files" --previous-target-files "$recovery_baseline"
python3 "$bundle/ci/check-dual-network.py" --source "$PWD" --candidate "$dest" --target-files "$out/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files"
# Package the verified directory, never a potentially stale ZIP left by an older target.
python3 "$bundle/ci/package-current-target.py" --source "$PWD" --target-files "$out/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files" --native-ota "$dest/$(basename "${zips[0]}")" --output "$dest/unsigned-target_files.zip" --report "$dest/packaging-input-audit.json"
sha256sum "$dest/"*.zip > "$dest/SHA256SUMS"
# No release promotion: private signing/migration and device acceptance remain mandatory.
state candidate-needs-acceptance
echo "Candidate retained locally: $dest"
