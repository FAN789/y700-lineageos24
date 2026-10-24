#!/usr/bin/env python3
"""Require preservation code, unchanged safety boundaries and packaged output."""
from pathlib import Path
import argparse,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path);a=p.parse_args();s=a.source
cpp=s/'system/update_engine/payload_consumer/postinstall_runner_action.cc'
assert 'if (partition.name == "system")' in cpp.read_text()
assert 'backuptool_failed = true;' in cpp.read_text()
framework=s/'frameworks/av/media/codec2/hal/client/client.cpp'
assert 'null HIDL configurable.' in framework.read_text() and 'getConfigurable transaction failed:' in framework.read_text()
for name in ['backuptool_ab.sh','backuptool_postinstall.sh']:
 t=(s/'vendor/lineage/prebuilt/common/bin'/name).read_text()
 assert '|| exit $?' in t or '|| return $?' in t
ab=(s/'vendor/lineage/prebuilt/common/bin/backuptool_ab.sh').read_text()
assert '/data/adb/magisk/addon.d.sh' in ab and '99-magisk.sh' in ab
assert 'run_stages pre-restore restore post-restore ||' in ab
target=s/'out/target/product/asphalt/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files'
if a.candidate:
 report=json.loads((a.candidate/'ota-inspection.json').read_text())
 meta=report['metadata'];assert meta.get('ota-wipe','no') not in ['yes','true','1'] and meta.get('ota-downgrade','no') not in ['yes','true','1']
 assert meta['ota-type']=='AB'
 for n in ['backuptool_ab.sh','backuptool_postinstall.sh']:
  assert (target/'SYSTEM/bin'/n).read_bytes()==(s/'vendor/lineage/prebuilt/common/bin'/n).read_bytes(),n+' packaged script mismatch'
 engine=(target/'SYSTEM/bin/update_engine').read_bytes();assert b'Running addon.d backup/restore for system' in engine
 for lib in ['SYSTEM/lib64/libcodec2_client.so','SYSTEM/lib/libcodec2_client.so']:
  assert b'null HIDL configurable.' in (target/lib).read_bytes(),'Media guard missing from packaged '+lib
 for forbidden in ['userdata','metadata','abl','persist','modemst1','modemst2','fsg']:
  assert not (target/'IMAGES'/(forbidden+'.img')).exists(),'Unexpected data/firmware image: '+forbidden
 payload_props=(target/'META/postinstall_config.txt').read_text();assert 'RUN_POSTINSTALL_system=true' in payload_props
 result={'passed':True,'system_addond_only':True,'preservation_errors_fatal':True,'installed_magisk_bootstrap_packaged':True,'media_guard_source_present':True,'no_data_wipe_metadata':True,'no_private_data_or_abl_images':True,'standard_system_postinstall':True,'device_validation_pending':True}
 (a.candidate/'preservation-build-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
else:print('Preservation source gates passed; candidate/device validation still required.')
