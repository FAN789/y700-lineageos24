#!/usr/bin/env python3
"""Verify native Settings implementation and packaged artifact preservation."""
from pathlib import Path
import argparse,json,hashlib,zipfile,io
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--target-files',type=Path);p.add_argument('--previous-target-files',type=Path);p.add_argument('--candidate',type=Path);a=p.parse_args();s=a.source
flags=s/'vendor/lineage/release/aconfig/cp2a/com.android.settings.connectivity'
v=(flags/'ethernet_settings.textproto').read_text();assert 'name: "ethernet_settings"' in v and 'state: ENABLED' in v and 'permission: READ_ONLY' in v
assert '"*/Android.bp"' in (flags.parent/'Android.bp').read_text()
bp=(flags/'Android.bp').read_text();assert 'package: "com.android.settings.connectivity"' in bp and 'srcs: ["*.textproto"]' in bp
n=s/'packages/apps/Settings';code=(n/'src/com/android/settings/network/ethernet/EthernetInterfaceDetailsController.kt').read_text()
for token in ['gatewayPref?.summary','dnsPref?.summary','macAddressPref?.summary','R.string.ethernet_config_title','R.string.ethernet_interface_title','it.address is Inet4Address','getLinkAddresses()']:
 assert token in code,token
xml=(n/'res/xml/ethernet_interface_details.xml').read_text();assert '@string/ethernet_gateway' in xml
for key in ['ethernet_ip_address','ethernet_gateway','ethernet_dns','ethernet_mac_address']:assert 'android:key="'+key+'"' in xml
for key in ['ethernet_tx_link_speed','ethernet_rx_link_speed','android:key="metered"']:assert key not in xml
iface=(n/'src/com/android/settings/network/ethernet/EthernetInterface.kt').read_text()
assert 'Handler(Looper.getMainLooper())' in iface
assert 'registerNetworkCallback(networkRequest, networkCallback, mainHandler)' in iface
assert 'registerNetworkCallback(networkRequest, networkCallback)' not in iface
tracker=(n/'src/com/android/settings/network/ethernet/EthernetTrackerImpl.kt').read_text()
assert 'ethernetInterfaces[id]?.onInterfaceStateChanged(id, state, role, cfg)' in tracker
assert 'ethernetInterfaces.keys.retainAll(present)' in tracker
assert 'ethernetManager?.interfaceList.orEmpty()' in tracker
assert 'ethernetManager?.availableInterfaces' not in tracker
assert tracker.index('interfaceListeners.add(listener)') < tracker.index('ethernetManager?.addInterfaceStateListener')
parent=(n/'src/com/android/settings/network/NetworkProviderSettings.java').read_text()
assert parent.count('this::onInterfaceListChanged')==1
assert 'registerInterfaceListener(mEthernetInterfaceListener)' in parent and 'unregisterInterfaceListener(mEthernetInterfaceListener)' in parent
report={'source_native_flag_and_details_passed':True,'kernel_changes_required':False,'device_written':False,'main_thread_callback_and_initial_state_source_verified':True}
if a.target_files:
 old=a.previous_target_files;assert old and old.is_dir();target=a.target_files
 srcjar=s/'out/soong/.intermediates/packages/apps/Settings/aconfig/settings_connectivity_flags_lib/android_common/gen/settings_connectivity_flags_lib.srcjar'
 with zipfile.ZipFile(srcjar) as z:
  java=z.read('com/android/settings/connectivity/Flags.java').decode();method=java.split('boolean ethernetSettings()',1)[1].split('}',1)[0];assert 'return true;' in method
 apk='SYSTEM_EXT/priv-app/Settings/Settings.apk';current=target/apk;previous=old/apk;assert current.is_file() and previous.is_file()
 def digest(path):return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
 assert digest(current)!=digest(previous),'Packaged Settings APK is stale'
 with zipfile.ZipFile(current) as z,zipfile.ZipFile(previous) as oz:
  dex=[name for name in z.namelist() if name.endswith('.dex')];assert dex
  assert any(z.read(name)!=oz.read(name) for name in dex),'Settings bytecode did not change'
  assert z.testzip() is None
 # Include vendor_boot/recovery copies as well as vendor_dlkm. The latter alone
 # contains 383 files; the preserved whole target-files baseline has 711 paths.
 newmods={str(v.relative_to(target)):v for v in target.rglob('*.ko') if v.is_file() and not v.is_symlink()}
 oldmods={str(v.relative_to(old)):v for v in old.rglob('*.ko') if v.is_file() and not v.is_symlink()}
 assert newmods.keys()==oldmods.keys() and len(newmods)==711
 for name in oldmods:assert digest(newmods[name])==digest(oldmods[name]),'Unrelated kernel module changed: '+name
 policy=['SYSTEM/etc/selinux/plat_sepolicy.cil','SYSTEM_EXT/etc/selinux/system_ext_sepolicy.cil','VENDOR/etc/selinux/vendor_sepolicy.cil','RECOVERY/RAMDISK/system/etc/selinux/plat_sepolicy.cil']
 checked=[]
 for name in policy:
  if (old/name).exists():assert (target/name).exists() and digest(target/name)==digest(old/name),name;checked.append(name)
 assert checked
 report.update(generated_flag_enabled=True,actual_settings_apk_changed=True,all_711_modules_unchanged=True,unchanged_policies=checked,settings_apk_sha256=digest(current),verifier_sha256=digest(Path(__file__)))
 if a.candidate:(a.candidate/'native-ethernet-acceptance.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
