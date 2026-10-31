"""Reject stale target-files before creating an archive or invoking any tool."""
from pathlib import Path
import tempfile,zipfile,subprocess,sys,json
with tempfile.TemporaryDirectory() as temp:
 d=Path(temp);t=d/'target';(t/'SYSTEM').mkdir(parents=True)
 ota=d/'ota.zip'
 with zipfile.ZipFile(ota,'w') as z:z.writestr('META-INF/com/android/metadata','post-build-incremental=1793401248\npost-timestamp=1793401248\npost-security-patch-level=2026-10-01\n')
 (t/'SYSTEM/build.prop').write_text('ro.build.version.incremental=1793357651\nro.build.date.utc=1793357651\nro.build.version.security_patch=2026-10-01\n')
 out=d/'unsigned.zip'
 r=subprocess.run([sys.executable,str(Path(__file__).with_name('package-current-target.py')),'--source',str(d/'no-build-tools'),'--target-files',str(t),'--native-ota',str(ota),'--output',str(out),'--report',str(d/'report.json')],capture_output=True,text=True)
 assert r.returncode!=0 and 'AssertionError' in r.stderr and 'FileNotFoundError' not in r.stderr and not out.exists()
 print(json.dumps({'stale_target_rejected_before_packaging':True,'build_system_invoked':False}))
