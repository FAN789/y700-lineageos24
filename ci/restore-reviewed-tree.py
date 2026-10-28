#!/usr/bin/env python3
from pathlib import Path
import argparse
from reviewed_patches import plan,snapshot,git
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args()
plans=plan(a.bundle,a.source)
for item in plans:
 repo=item['repo'];assert snapshot(repo,item['allowed'])==item['before'],'Concurrent source edit'
 for patch in reversed(item['applied']):git(repo,'apply','--reverse','--check',str(patch));git(repo,'apply','--reverse',str(patch))
 assert snapshot(repo,item['allowed'])==b'','Unreviewed changes remain'
print('Only byte-exact reviewed patch prefixes reversed; unrelated and staged edits refused')
