#!/usr/bin/env python3
from pathlib import Path
import argparse
from reviewed_patches import plan,snapshot,git
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--mode',choices=['baseline','tracking'],required=True);a=p.parse_args()
plans=plan(a.bundle,a.source,a.mode)
for item in plans:
 repo=item['repo'];assert snapshot(repo,item['allowed'])==item['before'],'Concurrent source edit'
 for patch in item['pending']:git(repo,'apply','--check',str(patch));git(repo,'apply',str(patch))
 assert snapshot(repo,item['allowed'])==item['final'],'Applied tree differs from exact reviewed patch sequence'
 git(repo,'diff','--check')
print('Exact reviewed patch sequences checked/applied; unknown edits preserved and refused')
