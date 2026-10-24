#!/usr/bin/env python3
"""Check sandbox/security support in the actual native-extracted OTA kernel."""
from pathlib import Path
import argparse,hashlib,json,struct,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
boot=a.candidate/'offline-validation/images/boot.img'
with boot.open('rb') as f:
 h=f.read(4096);assert h[:8]==b'ANDROID!' and struct.unpack_from('<I',h,40)[0]==4
 size=struct.unpack_from('<I',h,8)[0];kernel=f.read(size);assert len(kernel)==size
with tempfile.TemporaryDirectory(prefix='y700-kernel-check-') as td:
 k=Path(td)/'kernel';k.write_bytes(kernel)
 r=subprocess.run(['/bin/bash',str(a.source/'kernel/lenovo/sm8475/scripts/extract-ikconfig'),str(k)],capture_output=True,check=True)
cfg=dict(l.split('=',1) for l in r.stdout.decode().splitlines() if '=' in l and not l.startswith('#'))
required=['CONFIG_USER_NS','CONFIG_PID_NS','CONFIG_IPC_NS','CONFIG_POSIX_MQUEUE','CONFIG_SECURITY_SELINUX','CONFIG_SECCOMP','CONFIG_SECCOMP_FILTER']
assert all(cfg.get(k)=='y' for k in required),'Required sandbox/security support absent from actual OTA kernel'
assert cfg.get('CONFIG_SYSVIPC') is None,'Unexpected SYSVIPC configuration'
result={'passed':True,'actual_ota_kernel_sha256':hashlib.sha256(kernel).hexdigest(),'required_config':{k:cfg[k] for k in required},'SYSVIPC':'disabled','data_formatted':False,'device_tested':False}
(a.candidate/'kernel-preservation-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
