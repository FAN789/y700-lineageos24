from pathlib import Path
import argparse,subprocess,sys,json
p=argparse.ArgumentParser();p.add_argument('--source',required=True);a=p.parse_args();source=Path(a.source).resolve();out=source/'out';out.mkdir(exist_ok=True)
ns=source/'prebuilts/build-tools/linux-x86/bin/nsjail';assert ns.is_file()
cmd=[str(ns),'-H','android-build','-e','-u','nobody','-g','nogroup','-R','/','-B','/tmp','-R',str(source),'-B',str(out),'--disable_clone_newcgroup','--','/bin/bash','-c','if [ $(hostname) == "android-build" ]; then echo "Android" "Success"; else echo Failure; fi']
r=subprocess.run(cmd,cwd=source,capture_output=True,text=True,timeout=45)
if r.returncode or 'Android Success' not in r.stdout:
 print('Native Android build sandbox failed; refusing unsandboxed execution.',file=sys.stderr);print(r.stderr[-7000:],file=sys.stderr);raise SystemExit(1)
print('Native Android nsjail sandbox: passed')
