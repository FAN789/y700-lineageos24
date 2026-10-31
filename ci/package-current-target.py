"""Package an existing target-files directory without invoking the build system."""
from pathlib import Path
import argparse,hashlib,json,os,stat,subprocess,zipfile
a=argparse.ArgumentParser(description=__doc__)
for n in ['source','target-files','native-ota','output','report']:a.add_argument('--'+n,type=Path,required=True)
v=a.parse_args();t=v.target_files.resolve();out=v.output.resolve()
assert t.is_dir() and not out.exists() and out.parent.is_dir()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
with zipfile.ZipFile(v.native_ota) as z:
 assert z.testzip() is None
 meta=dict(l.split('=',1) for l in z.read('META-INF/com/android/metadata').decode().splitlines() if '=' in l)
props=dict(l.split('=',1) for l in (t/'SYSTEM/build.prop').read_text().splitlines() if '=' in l)
assert props['ro.build.version.incremental']==meta['post-build-incremental']
assert props['ro.build.date.utc']==meta['post-timestamp']
assert props['ro.build.version.security_patch']==meta['post-security-patch-level']
files={}
for root,dirs,names in os.walk(t,followlinks=False):
 for name in dirs[:]+names:
  p=Path(root)/name;mode=p.lstat().st_mode;rel=p.relative_to(t).as_posix()
  if stat.S_ISLNK(mode):
   if name in dirs:dirs.remove(name)
   raw=os.readlink(p).encode();files[rel]={'type':'symlink','sha256':hashlib.sha256(raw).hexdigest(),'mode':stat.S_IMODE(mode)}
  elif stat.S_ISREG(mode):files[rel]={'type':'file','sha256':sha(p),'mode':stat.S_IMODE(mode)}
  else:assert stat.S_ISDIR(mode),'Unexpected target-files special entry: '+rel
subprocess.run([str(v.source/'out/host/linux-x86/bin/soong_zip'),'-o',str(out),'-L','1','-parallel','3','-d','-C',str(t),'-D',str(t)],check=True)
with zipfile.ZipFile(out) as z:
 names=z.namelist();assert len(names)==len(set(names))
 assert {n for n in names if not n.endswith('/')}==set(files),'Archive member set differs from source directory'
 for rel,record in files.items():
  info=z.getinfo(rel)
  with z.open(info) as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  assert actual==record['sha256'],'Archive content differs: '+rel
  mode=info.external_attr>>16
  assert stat.S_ISLNK(mode)==(record['type']=='symlink'),'Symlink type changed: '+rel
  assert bool(mode&0o111)==bool(record['mode']&0o111),'Executable mode changed: '+rel
  p=t/rel
  assert (hashlib.sha256(os.readlink(p).encode()).hexdigest() if p.is_symlink() else sha(p))==record['sha256'],'Source changed during packaging: '+rel
r={'passed':True,'firmware_recompiled':False,'incremental':meta['post-build-incremental'],'native_ota_sha256':sha(v.native_ota),'target_files_sha256':sha(out),'every_file_and_symlink_verified':len(files),'files':files}
v.report.write_text(json.dumps(r,indent=2));print(json.dumps({k:x for k,x in r.items() if k!='files'}))
