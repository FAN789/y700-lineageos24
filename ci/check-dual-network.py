"""Check scoped dual-network source and actual signed Settings/Connectivity payload classes."""
from pathlib import Path
import argparse,json,zipfile,subprocess,tempfile,hashlib,os
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--target-files',type=Path);p.add_argument('--candidate',type=Path);a=p.parse_args();s=a.source;n=s/'packages/modules/Connectivity/service/src/com/android/server/connectivity';settings=s/'packages/apps/Settings'
policy=(n/'Y700DualNetworkPolicy.java').read_text();rule=(n/'Y700RouteRule.java').read_text();rank=(n/'NetworkRanker.java').read_text();cs=(s/'packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java').read_text();ui=(settings/'src/com/android/settings/network/Y700DualNetworkPreferenceController.java').read_text()
for token in ['"asphalt".equals(Build.DEVICE)','beforeRematch','cleanupOwnedRules','vpnPresent','defaultNetwork.linkProperties.getDnsServers()','new Y700RouteRule(host, internetTable, mark, 17)','onLink(address, ethernet)','isOwnAddress(address, wifi)']:assert token in policy,token
assert 'ProcessBuilder' not in policy and 'Runtime.getRuntime' not in policy
assert 'MARK_MASK = 0x1ffff' in rule and 'OWNER_PROTOCOL = 242' in rule
rank=rank[rank.index('@Nullable public <T extends Scoreable> T getBestNetworkByPolicy'): ]
assert rank.index('POLICY_IS_VPN),')<rank.index('final int preferredTransport = mConf.preferredTransport()')
assert rank.index('final int preferredTransport = mConf.preferredTransport()')<rank.index('POLICY_IS_VALIDATED)')
assert cs.index('mY700DualNetworkPolicy.beforeRematch')<cs.index('final NetworkReassignment changes = computeNetworkReassignment')
assert 'handleAlwaysOnNetworkRequest(mDefaultWifiRequest, keepBoth || wifiAlwaysRequested)' in cs
assert 'handleAlwaysOnNetworkRequest(mY700EthernetRequest, keepBoth)' in cs
keep_both=policy.split('public static boolean keepBoth(Context context)',1)[1].split('private static',1)[0]
assert 'return supported();' in keep_both and 'targets(context)' not in keep_both
assert 'users.isAdminUser()' in ui and 'registerContentObserver' in ui
for name in ['res/values/y700_dualnet.xml','res/values-zh-rCN/y700_dualnet.xml']:assert (settings/name).exists()
# Final user scope: a single three-choice outlet control, no per-device input.
xml=(settings/'res/xml/network_provider_settings.xml').read_text()
assert 'y700_dual_network_ethernet_hosts' not in xml and '<EditTextPreference' not in xml
assert 'mTargets' not in ui and 'normalizeHosts' not in ui and 'TARGETS' not in ui
pref=(settings/'src/com/android/settings/wifi/WifiEntryPreference.java').read_text()
assert pref.index('setSummary(summary);') < pref.index('mContentDescription = buildContentDescription();')
assert '"asphalt".equals(android.os.Build.DEVICE)' in pref
assert 'WifiEntry.CONNECTED_STATE_CONNECTED' in pref and '!mWifiEntry.isDefaultNetwork() && TextUtils.isEmpty(summary)' in pref
for v in ['values','values-zh-rCN']:
 text=(settings/('res/'+v+'/y700_dualnet.xml')).read_text()
 assert 'name="y700_dualnet_hosts"' not in text and '%4$' not in text
 assert 'y700_wifi_connected_secondary' in text
result={'source_passed':True,'device_written':False,'kernel_policy_changes_required':False,'native_process_shared_kernel_rules':True}
if a.target_files:
 t=a.target_files;apk=t/'SYSTEM_EXT/priv-app/Settings/Settings.apk'
 with zipfile.ZipFile(apk) as z:
  dex=b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex'));assert b'Lcom/android/settings/network/Y700DualNetworkPreferenceController;' in dex
 # Deapexer is used against the actual signed APEX, not a loose compilation intermediate.
 apex=t/'SYSTEM/apex/com.android.tethering.apex'
 if not apex.exists():apex=t/'SYSTEM/apex/com.android.tethering.capex'
 assert apex.exists(),str(apex)
 tools=s/'out/host/linux-x86/bin'
 with tempfile.TemporaryDirectory(prefix='y700-signed-connectivity-') as td:
  out=Path(td)/'extracted';extract_apex=apex
  if apex.suffix=='.capex':
   extract_apex=Path(td)/'original.apex'
   with zipfile.ZipFile(apex) as z:extract_apex.write_bytes(z.read('original_apex'))
  command=[str(tools/'deapexer'),'--debugfs_path',str(tools/'debugfs_static'),'--fsckerofs_path',str(tools/'fsck.erofs'),'extract',str(extract_apex),str(out)]
  r=subprocess.run(command,capture_output=True,text=True);assert r.returncode==0,r.stderr[-1500:]
  jars=list(out.rglob('service-connectivity.jar'));assert len(jars)==1,[str(x) for x in jars]
  with zipfile.ZipFile(jars[0]) as z:dex=b''.join(z.read(n) for n in z.namelist() if n.endswith('.dex'))
  # The Connectivity APEX jarjar rules relocate server classes in the shipped DEX.
  for cls in ['Y700DualNetworkPolicy','Y700RouteRule']:assert ('Landroid/net/connectivity/com/android/server/connectivity/'+cls+';').encode() in dex,cls
  result.update(signed_settings_apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(),signed_connectivity_apex_sha256=hashlib.sha256(apex.read_bytes()).hexdigest(),signed_connectivity_jar_sha256=hashlib.sha256(jars[0].read_bytes()).hexdigest(),actual_signed_payload_classes_verified=True)
 if a.candidate:(a.candidate/'dual-network-acceptance.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
