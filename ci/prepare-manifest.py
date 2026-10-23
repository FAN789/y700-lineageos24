#!/usr/bin/env python3
import argparse,xml.etree.ElementTree as ET
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--mode',choices=['baseline','tracking'],required=True);a=p.parse_args()
t=ET.parse(a.bundle/'manifests/resolved-manifest.xml')
for r in t.findall('remote'):
 if r.get('name')=='github':r.set('fetch','https://github.com')
for project in t.findall('project'):
 if a.mode=='tracking' and project.get('name','').startswith('LineageOS/'):
  branch=project.get('upstream','')
  if branch.startswith('refs/heads/lineage-24.0'):
   project.set('revision',branch)
target=a.source/'.repo/manifests/y700-ci.xml';target.parent.mkdir(parents=True,exist_ok=True)
t.write(target,encoding='utf-8',xml_declaration=True)
print('Manifest prepared:',a.mode)
