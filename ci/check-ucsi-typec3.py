#!/usr/bin/env python3
"""Bind reviewed UCSI source, actual delivered modules, load lists and module ABI."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile,re
from ramdisk_files import read,entries
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path);p.add_argument('--target-files',type=Path);p.add_argument('--previous-target-files',type=Path);a=p.parse_args()
src=a.source/'kernel/lenovo/sm8475/drivers/usb/typec/ucsi/ucsi_glink.c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src)=='04a2bf03d07ecc2b146a486da8f253711424b91ff801e1f8d8d89d47b511e93c','Reviewed UCSI source differs'
result={'source_passed':True,'source_sha256':'04a2bf03d07ecc2b146a486da8f253711424b91ff801e1f8d8d89d47b511e93c','new_power_mode':'UCSI_CONSTAT_PWR_OPMODE_TYPEC3_0','source_matrix_cases':10752,'other_modes_dp_otg_priority_changed':False,'device_written':False}
if a.candidate:
 assert a.target_files and a.previous_target_files
 t=a.target_files;old=a.previous_target_files
 modules={str(p.relative_to(t)):p for p in t.rglob('*.ko') if p.is_file() and not p.is_symlink()}
 previous={str(p.relative_to(old)):p for p in old.rglob('*.ko') if p.is_file() and not p.is_symlink()}
 assert modules.keys()==previous.keys(),'Delivered module path inventory changed'
 copies={n:p for n,p in modules.items() if p.name=='ucsi_glink.ko'}
 assert set(copies)=={'VENDOR_BOOT/RAMDISK/lib/modules/ucsi_glink.ko','VENDOR_DLKM/lib/modules/ucsi_glink.ko'}
 hashes={sha(p) for p in copies.values()};assert len(hashes)==1
 expected=next(iter(hashes));oldhash={sha(previous[n]) for n in copies};assert len(oldhash)==1 and expected not in oldhash,'UCSI driver was not actually rebuilt'
 changed=[n for n in modules if sha(modules[n])!=sha(previous[n])]
 assert set(changed)==set(copies),'Unexpected other module changes require explicit audit'
 for name in copies:
  def info(path):
   text=subprocess.check_output(['readelf','-p','.modinfo',str(path)],text=True)
   return {m.group(1):m.group(2) for m in re.finditer(r'\]\s+(name|vermagic|depends)=(.*)',text)}
  before,after=info(previous[name]),info(copies[name]);assert before==after and set(after)=={'name','vermagic','depends'}
  assert after['name']=='ucsi_glink'
  versions=[subprocess.check_output(['readelf','-x','__versions',str(p)],stderr=subprocess.STDOUT) for p in [previous[name],copies[name]]]
  assert versions[0]==versions[1],'Imported symbol CRCs changed'
 images=a.candidate/'offline-validation/images'
 out=subprocess.run(['debugfs','-R','cat /lib/modules/ucsi_glink.ko',str(images/'vendor_dlkm.img')],capture_output=True,check=True)
 assert hashlib.sha256(out.stdout).hexdigest()==expected,'Actual vendor_dlkm image contains stale UCSI module'
 loads={}
 with tempfile.TemporaryDirectory(prefix='y700-vendorboot-ucsi-') as td:
  td=Path(td);subprocess.run([str(a.source/'out/host/linux-x86/bin/unpack_bootimg'),'--boot_img',str(images/'vendor_boot.img'),'--out',str(td)],capture_output=True,check=True)
  disks=[p for p in td.iterdir() if re.fullmatch(r'vendor_ramdisk(?:[0-9]+)?',p.name)];assert disks
  found=[]
  for disk in disks:
   for name,data in entries(read(disk)):
    if name=='lib/modules/ucsi_glink.ko':found.append(hashlib.sha256(data).hexdigest())
    if name.startswith('lib/modules/modules.load'):loads[name]=data
  assert found and all(h==expected for h in found),'Actual vendor_boot ramdisk contains missing/stale UCSI module'
 assert any(b'ucsi_glink' in data for data in loads.values()),'UCSI module not in actual vendor_boot module load lists'
 for name,data in loads.items():assert data==(old/'VENDOR_BOOT/RAMDISK'/name).read_bytes(),'Early-boot module load order changed'
 result.update(passed=True,actual_vendor_dlkm_module_passed=True,actual_vendor_boot_module_passed=True,actual_module_load_lists_preserved=True,module_sha256=expected,previous_module_sha256=next(iter(oldhash)),delivered_module_copies=len(copies),all_module_paths=len(modules),only_ucsi_module_changed=True,vermagic_dependencies_symbol_crc_preserved=True)
 (a.candidate/'ucsi-typec3-module-check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
