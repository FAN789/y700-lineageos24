#!/usr/bin/env python3
"""Verify Recovery ADSP initialization, exact policy scope and preserved binaries."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path);p.add_argument('--target-files',type=Path);p.add_argument('--previous-target-files',type=Path);a=p.parse_args()
s=a.source;repo=s/'device/lenovo/sm8475-common'
rc=(repo/'init/etc/init.qcom.recovery.rc').read_text()
trigger='on fs && property:ro.product.device=asphalt'
assert rc.count(trigger)==1
block=rc.split(trigger,1)[1].strip().splitlines()
expected=[
 'mkdir /firmware 0755 root root',
 'wait /dev/block/by-name/modem${ro.boot.slot_suffix} 5',
 'mount vfat /dev/block/by-name/modem${ro.boot.slot_suffix} /firmware ro nosuid nodev noexec shortname=lower,uid=1000,gid=1000,dmask=227,fmask=337,context=u:object_r:firmware_file:s0',
 'wait /firmware/image/adsp.mdt 5',
 'write /sys/module/firmware_class/parameters/path /firmware/image',
 'wait /sys/class/remoteproc/remoteproc1/state 5',
 'write /sys/class/remoteproc/remoteproc1/state start']
assert [l.strip() for l in block]==expected,'Unexpected Recovery startup scope/order'
types={'vendor_sysfs_recovery_firmware_path':'/module/firmware_class/parameters/path','vendor_sysfs_recovery_adsp_state':'/devices/platform/soc/3000000.remoteproc-adsp/remoteproc/remoteproc1/state'}
policy=(repo/'sepolicy/vendor/recovery_adsp.te').read_text();genfs=(repo/'sepolicy/vendor/genfs_contexts').read_text()
assert "recovery_only(`" in policy and "recovery_only(`" in genfs
assert 'allow init { vendor_sysfs_recovery_firmware_path vendor_sysfs_recovery_adsp_state }:file { getattr open write };' in policy
assert not any(x in policy for x in ['permissive ','allow init sysfs:',':capability','dontaudit','*'])
for t,path in types.items():assert genfs.count('genfscon sysfs '+path+' u:object_r:'+t+':s0')==1
result={'source_passed':True,'same_slot_stock_firmware_mount_readonly':True,'no_gpio_forcing':True,'recovery_only_exact_sysfs_labels':True}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cil(path):
 with tempfile.TemporaryDirectory() as td:
  out=Path(td)/'policy.cil'
  subprocess.run([str(s/'out/host/linux-x86/bin/checkpolicy'),'-M','-b','-C','-o',str(out),str(path)],capture_output=True,check=True)
  return out.read_text()
def parsed(text):
 attrs={};rules=[]
 for l in text.splitlines():
  l=l.strip();m=re.fullmatch(r'\(typeattributeset (\S+) \(([^()]*)\)\)',l)
  if m:attrs[m[1]]=set(m[2].split())
  m=re.fullmatch(r'\(allow (\S+) (\S+) \((\S+) \(([^()]*)\)\)\)',l)
  if m:rules.append((m[1],m[2],m[3],m[4].split()))
 return attrs,rules
def grants(text,source):
 attrs,rules=parsed(text);out=set()
 for src,tgt,cl,permissions in rules:
  if src!=source and source not in attrs.get(src,set()):continue
  targets=attrs.get(tgt,{source} if tgt=='self' else {tgt})
  for t in targets:
   if t not in types:out.update((t,cl,q) for q in permissions)
 return out
if a.candidate:
 assert a.target_files and a.previous_target_files
 t=a.target_files;old=a.previous_target_files;r=t/'RECOVERY/RAMDISK'
 assert (r/'system/etc/init/init.qcom.recovery.rc').read_text()==rc
 oldcil,newcil=cil(old/'RECOVERY/RAMDISK/sepolicy'),cil(r/'sepolicy')
 for typ,path in types.items():
  assert '(type '+typ+')' in newcil and typ not in oldcil
  assert any(l.startswith('(genfscon sysfs ') and path in l and typ in l for l in newcil.splitlines())
 assert grants(oldcil,'init')==grants(newcil,'init'),'Init gained permissions to an existing unrelated target'
 attrs,rules=parsed(newcil)
 for typ in types:
  allowed=set()
  for src,tgt,cl,permissions in rules:
   if (src=='init' or 'init' in attrs.get(src,set())) and (tgt==typ or typ in attrs.get(tgt,set())) and cl=='file':allowed.update(permissions)
  assert {'open','write','getattr'}<=allowed
 assert not any(src=='init' and tgt=='sysfs' and cl=='file' and 'write' in permissions for src,tgt,cl,permissions in rules)
 def permissives(path):return subprocess.check_output([str(s/'out/host/linux-x86/bin/sepolicy-analyze'),str(path),'permissive'],text=True).splitlines()
 assert permissives(old/'RECOVERY/RAMDISK/sepolicy')==permissives(r/'sepolicy'),'New permissive domain'
 normal=[]
 for part in ['SYSTEM','SYSTEM_EXT','PRODUCT','VENDOR','ODM']:
  folder=t/part/'etc/selinux'
  for f in folder.glob('*'):
   if f.is_file() and (f.suffix=='.cil' or f.name=='precompiled_sepolicy'):
    before=old/f.relative_to(t);assert before.is_file() and sha(f)==sha(before),'Normal Android policy changed: '+str(f.relative_to(t));normal.append(str(f.relative_to(t)))
 assert normal
 modules={str(f.relative_to(t)):sha(f) for f in t.rglob('*.ko') if f.is_file() and not f.is_symlink()}
 previous={str(f.relative_to(old)):sha(f) for f in old.rglob('*.ko') if f.is_file() and not f.is_symlink()}
 assert modules==previous,'Recovery init fix changed a module'
 assert len(modules)==711
 assert (t/'VENDOR/etc/init/hw/init.target.rc').read_bytes()==(old/'VENDOR/etc/init/hw/init.target.rc').read_bytes()
 kernel=json.loads((a.candidate/'kernel-preservation-check.json').read_text())
 assert kernel['actual_ota_kernel_sha256']=='d49e3fe5d2203523e9b20523b500ea69e41c8de72f7ceeff5a90d283e0d0d16c'
 result.update(passed=True,actual_recovery_policy_verified=True,normal_policy_files_unchanged=normal,all_711_module_paths_and_bytes_unchanged=True,core_kernel_unchanged=True,unrelated_init_permissions_unchanged=True,no_new_permissive_domain=True,device_flash_authorized=False)
 (a.candidate/'recovery-adsp-check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
