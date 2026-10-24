#!/usr/bin/env python3
"""Exercise real addon.d scripts in isolated filesystem fixtures, never devices."""
from pathlib import Path
import argparse,os,re,subprocess,tempfile,json
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
src=a.source/'vendor/lineage/prebuilt/common/bin'
ab=(src/'backuptool_ab.sh').read_text();post=(src/'backuptool_postinstall.sh').read_text();functions=(src/'backuptool_ab.functions').read_text()
results=[]
for case in ['rooted','unrooted','gapps-fails','magisk-fails','incomplete-magisk','existing-hook','copy-failure-swallowed','move-failure-swallowed','copy-corruption-swallowed']:
 with tempfile.TemporaryDirectory(prefix='y700-preservation-test-') as td:
  r=Path(td)
  def write(name,text,mode=0o644):
   q=r/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text);q.chmod(mode);return q
  def relocate(text):
   text=re.sub(r'(?<![\w/])/(system|system_ext|postinstall|data|vendor|product)\b',lambda m:str(r/m[1]),text)
   return re.sub(r'^#![^\n]*','#!/bin/sh',text,count=1)
  write('system/build.prop','ro.lineage.version=24.0-test\n')
  write('system/product/retained-app','original-gapps-bytes')
  (r/'system/product/retained-link').symlink_to('retained-app')
  write('postinstall/system/boot.img','unpatched-target')
  log=r/'stages';log.write_text('')
  addon='''#!/bin/sh
# ADDOND_VERSION=3
. "$TEST_ROOT/postinstall/tmp/backuptool.functions"
echo "gapps:$1" >> "$TEST_LOG"
case "$1" in
 backup) for f in retained-app retained-link; do backup_file "$S/product/$f"; done; : ;;
 restore) for f in retained-app retained-link; do restore_file "$S/product/$f"; done; : ;;
 post-restore) [ "$TEST_CASE" != gapps-fails ] || exit 23 ;;
esac
exit 0
'''
  write('system/addon.d/30-gapps.sh',addon,0o755)
  magisk='''#!/bin/sh
# ADDOND_VERSION=2
[ "$ADDOND_VERSION" = 2 ] || exit 29
echo "magisk:$1" >> "$TEST_LOG"
if [ "$1" = post-restore ]; then
 [ "$TEST_CASE" != magisk-fails ] || exit 31
 printf patched-target > "$TEST_ROOT/postinstall/system/boot.img"
fi
exit 0
'''
  if case!='unrooted':
   write('data/adb/magisk/addon.d.sh',magisk,0o755)
   if case!='incomplete-magisk':
    write('data/adb/magisk/util_functions.sh','fixture utility\n')
    write('data/adb/magisk/magiskboot','#!/bin/sh\nexit 0\n',0o755)
  if case=='existing-hook':write('system/addon.d/99-magisk.sh',magisk+'# existing hook retained\n',0o755)
  write('postinstall/system/bin/backuptool_ab.sh',relocate(ab),0o755)
  wrapper=write('postinstall/system/bin/backuptool_postinstall.sh',relocate(post),0o755)
  write('postinstall/system/bin/backuptool_ab.functions',relocate(functions))
  for command in ['mount','umount','mountpoint','sync','blockdev']:write('fakebin/'+command,'#!/bin/sh\nexit 0\n',0o755)
  write('fakebin/getprop','#!/bin/sh\ncase "$1" in ro.boot.dynamic_partitions) echo false;; ro.boot.slot_suffix) echo _b;; ro.boot.hardware) echo qcom;; esac\n',0o755)
  write('fakebin/cp',r'''#!/bin/sh
dest=""
for arg; do dest=$arg; done
case "$dest" in */backupdir/*/retained-app)
 if [ "$TEST_CASE" = copy-failure-swallowed ]; then exit 37; fi
 if [ "$TEST_CASE" = copy-corruption-swallowed ]; then
  /bin/cp "$@" || exit $?
  printf corrupt > "$dest"
  exit 0
 fi
;; esac
exec /bin/cp "$@"
''',0o755)
  write('fakebin/mv',r'''#!/bin/sh
dest=""
for arg; do dest=$arg; done
case "$dest" in */postinstall/product/retained-app)
 [ "$TEST_CASE" != move-failure-swallowed ] || exit 41
;; esac
exec /bin/mv "$@"
''',0o755)
  env={**os.environ,'PATH':str(r/'fakebin')+':'+os.environ['PATH'],'TEST_LOG':str(log),'TEST_ROOT':str(r),'TEST_CASE':case}
  proc=subprocess.run(['/bin/sh',str(wrapper)],env=env,capture_output=True,text=True,timeout=20)
  success=case in ['rooted','unrooted','existing-hook'];assert (proc.returncode==0)==success,(case,proc.returncode,proc.stdout,proc.stderr)
  if success:
   assert (r/'postinstall/product/retained-app').exists(),(case,proc.stdout,proc.stderr,log.read_text(),[str(p.relative_to(r)) for p in r.rglob('*') if p.is_file()])
   assert (r/'postinstall/product/retained-app').read_bytes()==b'original-gapps-bytes'
   assert (r/'postinstall/product/retained-link').is_symlink() and os.readlink(r/'postinstall/product/retained-link')=='retained-app'
   if case=='unrooted':
    assert not (r/'postinstall/system/addon.d/99-magisk.sh').exists()
    assert (r/'postinstall/system/boot.img').read_text()=='unpatched-target'
   else:
    assert (r/'postinstall/system/boot.img').read_text()=='patched-target'
    hook=r/'postinstall/system/addon.d/99-magisk.sh';assert hook.exists()
    if case=='existing-hook':assert 'existing hook retained' in hook.read_text()
  else:assert (r/'postinstall/system/boot.img').read_text()=='unpatched-target'
  results.append({'case':case,'exit':proc.returncode,'expected_success':success,'passed':True})
print(json.dumps({'passed':True,'tests':results,'no_block_devices_or_real_mounts_used':True}))
