#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--mode',choices=['baseline','tracking'],required=True);a=p.parse_args()
pending=[]
series=json.loads((a.bundle/'patches/series.json').read_text())
if (a.bundle/'ci/patches.json').exists():series+=json.loads((a.bundle/'ci/patches.json').read_text())
for item in series:
 repo=a.source/item['project'];patch=(a.bundle/'patches'/item['patch']).resolve()
 def git(*args):return subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
 head=git('rev-parse','HEAD');assert head.returncode==0,item['project']
 if a.mode=='baseline':assert head.stdout.strip()==item['base_commit'],item['project']
 else:assert git('merge-base','--is-ancestor',item['base_commit'],'HEAD').returncode==0,'Non-descendant upstream revision: '+item['project']
 status=git('status','--porcelain').stdout
 if git('apply','--reverse','--check',str(patch)).returncode==0:
  expected={line[6:] for line in patch.read_text().splitlines() if line.startswith('+++ b/')}
  actual={line[3:] for line in status.splitlines()}
  assert actual<=expected,'Unreviewed modifications: '+item['project']
  continue
 assert not status,'Unreviewed modifications: '+item['project']
 check=git('apply','--check',str(patch));assert check.returncode==0,check.stderr
 pending.append((repo,patch))
for repo,patch in pending:
 subprocess.run(['git','-C',str(repo),'apply',str(patch)],check=True)
 subprocess.run(['git','-C',str(repo),'diff','--check'],check=True)
print('Reviewed patches checked/applied without disabling native checks')
