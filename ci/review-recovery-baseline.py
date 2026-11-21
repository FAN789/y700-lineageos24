#!/usr/bin/env python3
"""Accept only exact policy deltas from reviewed upstream commits, with binary proof.

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
AUDIO_DUMP_RULES={
'(allow dumpstate vendor_qtiaudiohalvendorextn (binder (call transfer)))',
'(allow dumpstate vendor_qtiaudiohalvendorextn (fd (use)))',
'(allow vendor_qtiaudiohalvendorextn dumpstate (binder (transfer)))',
'(allow vendor_qtiaudiohalvendorextn dumpstate (fd (use)))',
'(allow vendor_qtiaudiohalvendorextn dumpstate (fifo_file (write)))'}
PEN_LABELS={
 '(genfscon proc "/edge_grid_zone" (u object_r proc_pen ((s0) (s0))))',
 '(genfscon proc "/panel_direction" (u object_r proc_pen ((s0) (s0))))'}
OVERLAY_CACHE_RULES={'(allow overlay_remounter cache_file (dir (search)))'}
REVIEWED_DELTAS=(
 ('device/qcom/sepolicy', 'a8385f33b31aac5ba7f001413f4d67c7c9bf632e',
  ('generic/private/dumpstate.te', 'generic/private/qtiaudiohalvendorextn.te'), AUDIO_DUMP_RULES),
 ('device/lenovo/asphalt', 'a6332f271a32d773f9b4675f3e081d5cf6c286b5',
  ('sepolicy/private/genfs_contexts',), PEN_LABELS),
 ('device/lineage/sepolicy', '058a97c7878264ad93541e1d1e871d04d65b4f4e',
  ('common/private/overlay_remounter.te',), OVERLAY_CACHE_RULES))
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
assert set(changed)=={'SYSTEM_EXT/etc/selinux/system_ext_sepolicy.cil','ODM/etc/selinux/precompiled_sepolicy'},changed
rel='SYSTEM_EXT/etc/selinux/system_ext_sepolicy.cil';before=semantic(O/rel);after=semantic(N/rel)
additions=after-before
expected=set();commits={}
for project,commit,paths,rules in REVIEWED_DELTAS:
 if additions.isdisjoint(rules):
  continue
 assert rules<=additions,'Partial reviewed normal CIL change: '+project
 repo=S/project
 subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=repo,check=True)
 subprocess.run(['git','diff','--quiet',commit,'--',*paths],cwd=repo,check=True)
 expected.update(rules)
 commits[project]=commit
assert not before-after and additions==expected,'Unreviewed normal CIL change'
for label,t in [('old',O),('new',N)]:
 subprocess.run([str(S/'out/host/linux-x86/bin/checkpolicy'),'-M','-b','-C','-o',str(W/(label+'-normal.cil')),str(t/'ODM/etc/selinux/precompiled_sepolicy')],capture_output=True,check=True)
before=semantic(W/'old-normal.cil');after=semantic(W/'new-normal.cil')
assert not before-after and after-before==expected,'Unreviewed binary policy change'
assert not view.exists(),'Existing baseline is immutable; use its recorded path or a new output directory'
shutil.copytree(O,view,symlinks=True,copy_function=os.link)
for rel in changed:
 dst=view/rel;dst.unlink();shutil.copy2(N/rel,dst)
record={'passed':True,'upstream_commits':commits,'exact_added_rules':sorted(expected),'no_removed_rules':True,'normal_source_and_binary_policy_delta_match':True,'recovery_policy_unchanged_from_original_baseline':sha(view/'RECOVERY/RAMDISK/sepolicy')==sha(O/'RECOVERY/RAMDISK/sepolicy'),'policy_files':records,'changed_files':changed,'original_baseline_immutable':True}
assert record['recovery_policy_unchanged_from_original_baseline']
(view.parent/(view.name+'-audit.json')).write_text(json.dumps(record,indent=2));print(str(view))
