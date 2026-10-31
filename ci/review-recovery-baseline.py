#!/usr/bin/env python3
"""Accept only the reviewed upstream audio-dump policy delta, including binary proof.

Recovery isolation, module and permissive checks remain in check-recovery-adsp.py.
All other policy drift fails closed and requires a separate review.
"""
from pathlib import Path
import subprocess,hashlib,json,shutil,os
import argparse,tempfile
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--target-files',type=Path,required=True);p.add_argument('--previous-target-files',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
S=a.source;O=a.previous_target_files;N=a.target_files;view=a.output
view.parent.mkdir(parents=True,exist_ok=True)
tmp=tempfile.TemporaryDirectory(prefix='recovery-baseline-',dir=view.parent);W=Path(tmp.name)
EXPECTED={
'(allow dumpstate vendor_qtiaudiohalvendorextn (binder (call transfer)))',
'(allow dumpstate vendor_qtiaudiohalvendorextn (fd (use)))',
'(allow vendor_qtiaudiohalvendorextn dumpstate (binder (transfer)))',
'(allow vendor_qtiaudiohalvendorextn dumpstate (fd (use)))',
'(allow vendor_qtiaudiohalvendorextn dumpstate (fifo_file (write)))'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def semantic(p):return {l.strip() for l in p.read_text().splitlines() if l.strip() and not l.lstrip().startswith(';')}
changed=[];records={}
for part in ['SYSTEM','SYSTEM_EXT','PRODUCT','VENDOR','ODM']:
 for f in (N/part/'etc/selinux').glob('*'):
  if not f.is_file() or (f.suffix!='.cil' and f.name!='precompiled_sepolicy'):continue
  rel=str(f.relative_to(N));b=O/rel;assert b.is_file()
  records[rel]={'old':sha(b),'new':sha(f)}
  if sha(b)!=sha(f):changed.append(rel)
if not changed:
 print(str(O));raise SystemExit(0)
repo=S/'device/qcom/sepolicy';commit='a8385f33b31aac5ba7f001413f4d67c7c9bf632e'
subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=repo,check=True)
assert not subprocess.check_output(['git','diff','--','generic/private/dumpstate.te','generic/private/qtiaudiohalvendorextn.te'],cwd=repo)
assert set(changed)=={'SYSTEM_EXT/etc/selinux/system_ext_sepolicy.cil','ODM/etc/selinux/precompiled_sepolicy'},changed
rel='SYSTEM_EXT/etc/selinux/system_ext_sepolicy.cil';before=semantic(O/rel);after=semantic(N/rel)
assert not before-after and after-before==EXPECTED,'Unreviewed normal CIL change'
for label,t in [('old',O),('new',N)]:
 subprocess.run([str(S/'out/host/linux-x86/bin/checkpolicy'),'-M','-b','-C','-o',str(W/(label+'-normal.cil')),str(t/'ODM/etc/selinux/precompiled_sepolicy')],capture_output=True,check=True)
before=semantic(W/'old-normal.cil');after=semantic(W/'new-normal.cil')
assert not before-after and after-before==EXPECTED,'Unreviewed binary policy change'
assert not view.exists(),'Existing baseline is immutable; use its recorded path or a new output directory'
shutil.copytree(O,view,symlinks=True,copy_function=os.link)
for rel in changed:
 dst=view/rel;dst.unlink();shutil.copy2(N/rel,dst)
record={'passed':True,'upstream_commit':commit,'exact_added_rules':sorted(EXPECTED),'no_removed_rules':True,'normal_source_and_binary_policy_delta_match':True,'recovery_policy_unchanged_from_original_baseline':sha(view/'RECOVERY/RAMDISK/sepolicy')==sha(O/'RECOVERY/RAMDISK/sepolicy'),'policy_files':records,'changed_files':changed,'original_baseline_immutable':True}
assert record['recovery_policy_unchanged_from_original_baseline']
(view.parent/(view.name+'-audit.json')).write_text(json.dumps(record,indent=2));print(str(view))
