#!/usr/bin/env python3
"""Reverse only byte-exact known build changes; refuse every unrelated edit."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args()
series=json.loads((a.bundle/'patches/series.json').read_text())
if (a.bundle/'ci/patches.json').exists():series+=json.loads((a.bundle/'ci/patches.json').read_text())
for item in series:
 repo=a.source/item['project'];patch=(a.bundle/'patches'/item['patch']).resolve()
 if not (repo/'.git').exists():continue
 def git(*args):return subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
 status=git('status','--porcelain');assert status.returncode==0
 if not status.stdout:continue
 reverse=git('apply','--reverse','--check',str(patch));assert reverse.returncode==0,'Unknown edit: '+item['project']
 expected=git('diff','--binary').stdout
 # Reverse in an isolated temporary index before touching the working tree.
 import os,tempfile
 with tempfile.TemporaryDirectory() as d:
  env={**os.environ,'GIT_INDEX_FILE':str(Path(d)/'index')}
  for args in [('read-tree','HEAD'),('add','-u'),('apply','--cached','--reverse',str(patch))]:
   subprocess.run(['git','-C',str(repo),*args],env=env,check=True,capture_output=True)
  check=subprocess.run(['git','-C',str(repo),'diff','--cached','--exit-code','HEAD'],env=env,capture_output=True)
  assert check.returncode==0,'Patch plus unrelated modifications: '+item['project']
 assert not git('ls-files','--others','--exclude-standard').stdout,'Untracked files: '+item['project']
 assert git('diff','--binary').stdout==expected,'Concurrent source edit'
 subprocess.run(['git','-C',str(repo),'apply','--reverse',str(patch)],check=True)
print('Only exact reviewed changes reversed for the next sync')
