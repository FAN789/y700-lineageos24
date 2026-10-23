#!/usr/bin/env python3
"""Exercise patch safety and OTA rejection without firmware builds."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,zipfile
bundle=Path(__file__).resolve().parents[1]
def run(*args,ok=True):
 r=subprocess.run(args,capture_output=True,text=True)
 assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
 return r
with tempfile.TemporaryDirectory() as d:
 root=Path(d);source=root/'source';repo=source/'component';repo.mkdir(parents=True);(root/'bundle/patches').mkdir(parents=True)
 run('git','-C',str(repo),'init');run('git','-C',str(repo),'config','user.email','test@localhost');run('git','-C',str(repo),'config','user.name','Test');run('git','-C',str(repo),'config','core.autocrlf','false')
 (repo/'file').write_text('one\n',newline='\n');run('git','-C',str(repo),'add','file');run('git','-C',str(repo),'commit','-m','base')
 head=run('git','-C',str(repo),'rev-parse','HEAD').stdout.strip();(repo/'file').write_text('two\n',newline='\n')
 (root/'bundle/patches/change.patch').write_text(run('git','-C',str(repo),'diff').stdout,newline='\n')
 (root/'bundle/patches/series.json').write_text(json.dumps([{'project':'component','patch':'change.patch','base_commit':head}]))
 args=[sys.executable,str(bundle/'ci/restore-reviewed-tree.py'),'--bundle',str(root/'bundle'),'--source',str(source)]
 run(*args);assert (repo/'file').read_text()=='one\n'
 apply=[sys.executable,str(bundle/'ci/apply-reviewed-patches.py'),'--bundle',str(root/'bundle'),'--source',str(source),'--mode','baseline']
 run(*apply);run(*apply);assert (repo/'file').read_text()=='two\n'
 (repo/'file').write_text('two\nUNRELATED\n',newline='\n');run(*args,ok=False);assert 'UNRELATED' in (repo/'file').read_text()
 (repo/'file').write_text('two\n',newline='\n');(repo/'personal').write_text('retain');run(*args,ok=False);assert (repo/'personal').exists()
 bad=root/'bad.zip'
 with zipfile.ZipFile(bad,'w') as z:z.writestr('META-INF/com/android/metadata','ota-type=AB\npre-device=another-tablet\n')
 run(sys.executable,str(bundle/'ci/ota-feed.py'),'inspect',str(bad),'--output',str(root/'result.json'),ok=False)
 assert not (root/'result.json').exists()
print('PASS: exact patch restore, idempotency, unrelated-edit preservation and wrong-device OTA rejection')
