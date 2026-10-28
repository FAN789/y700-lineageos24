#!/usr/bin/env python3
"""Verify the physical USB fix in source and actual native OTA images."""
from pathlib import Path, PurePosixPath
import argparse, gzip, hashlib, json, stat, subprocess, tempfile

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
p.add_argument('--candidate',type=Path);p.add_argument('--target-files',type=Path)
a=p.parse_args();s=a.source
guard='on property:sys.usb.controller=dummy_udc.0 && property:ro.boot.usbcontroller=a600000.dwc3'
files={'normal':s/'device/lenovo/sm8475-common/init/etc/init.target.rc',
       'recovery':s/'device/lenovo/sm8475-common/init/etc/init.qcom.recovery.rc'}
expected={name:path.read_bytes() for name,path in files.items()}
def actions(data):
    result=[];current=None
    for raw in data.decode().splitlines():
        line=raw.strip()
        if not line or line.startswith('#'):continue
        if not raw[0].isspace():
            current=[line,[]];result.append(current)
        elif current is not None:current[1].append(line)
    return result
for name,data in expected.items():
    matches=[cmd for trigger,cmd in actions(data) if trigger==guard]
    assert matches==[['setprop sys.usb.controller ${ro.boot.usbcontroller}']],name+' missing exact controller guard'
normal=actions(expected['normal']);setters=[trigger for trigger,cmd in normal if 'setprop vendor.usb.controller a600000.dwc3' in cmd]
assert setters==['on early-init'],'Vendor USB controller must be set before boot/HAL actions'
result={'source_passed':True,'kernel_or_partition_layout_changed_by_usb_patch':False}
if a.candidate:
    assert a.target_files is not None
    assert (a.target_files/'VENDOR/etc/init/hw/init.target.rc').read_bytes()==expected['normal']
    assert (a.target_files/'RECOVERY/RAMDISK/system/etc/init/init.qcom.recovery.rc').read_bytes()==expected['recovery']
    images=a.candidate/'offline-validation/images'
    output=subprocess.run(['debugfs','-R','cat /etc/init/hw/init.target.rc',str(images/'vendor.img')],capture_output=True,check=True)
    assert output.stdout==expected['normal'],'Actual vendor image has stale USB initialization'
    with tempfile.TemporaryDirectory(prefix='y700-recovery-usb-') as td:
        td=Path(td)
        subprocess.run([str(s/'out/host/linux-x86/bin/unpack_bootimg'),'--boot_img',str(images/'recovery.img'),'--out',str(td)],capture_output=True,check=True)
        ramdisk=td/'ramdisk';raw=ramdisk.read_bytes()
        if raw[:2]==b'\x1f\x8b':data=gzip.decompress(raw)
        elif raw[:6] in [b'070701',b'070702']:data=raw
        else:data=subprocess.check_output(['lz4','-dc',str(ramdisk)])
        offset=0;found=[]
        while offset<len(data):
            while offset<len(data) and data[offset]==0:offset+=1
            if offset==len(data):break
            header=data[offset:offset+110];assert len(header)==110 and header[:6] in [b'070701',b'070702']
            fields=[int(header[6+8*i:14+8*i],16) for i in range(13)]
            size,namesize=fields[6],fields[11];assert 0<namesize<65536
            name=data[offset+110:offset+110+namesize];assert name.endswith(b'\0')
            name=name[:-1].decode();start=(offset+110+namesize+3)&~3
            assert start+size<=len(data)
            path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts
            if str(path)=='system/etc/init/init.qcom.recovery.rc':
                assert stat.S_ISREG(fields[1]);found.append(data[start:start+size])
            offset=(start+size+3)&~3
        assert found==[expected['recovery']],'Actual recovery ramdisk has missing/stale/duplicate USB guard'
    result.update({'actual_vendor_image_passed':True,'actual_recovery_ramdisk_passed':True,
                   'normal_rc_sha256':hashlib.sha256(expected['normal']).hexdigest(),
                   'recovery_rc_sha256':hashlib.sha256(expected['recovery']).hexdigest(),
                   'same_original_computer_port_boot_test_pending':True,'device_written':False})
    (a.candidate/'usb-controller-check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
