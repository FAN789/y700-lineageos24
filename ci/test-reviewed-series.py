#!/usr/bin/env python3
"""Real-Git regression for layered patches, partial runs, new files and refusal."""
from pathlib import Path
import tempfile,subprocess,sys,json,difflib
ci=Path(__file__).resolve().parent

def run(*args,ok=True):
 r=subprocess.run([str(x) for x in args],capture_output=True,text=True)
 assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
 return r.stdout
with tempfile.TemporaryDirectory(prefix='y700-series-test-') as td:
 p=Path(td);repo=p/'source/component';repo.mkdir(parents=True);bundle=p/'bundle';(bundle/'patches').mkdir(parents=True)
 def git(*a):return run('git','-C',repo,*a)
 git('init');git('config','user.name','Fixture');git('config','user.email','fixture@localhost');git('config','core.autocrlf','false')
 (repo/'file').write_text('one\n');git('add','file');git('commit','-m','base');head=git('rev-parse','HEAD').strip()
 changes=[('one\n','two\n','a/file','b/file'),('two\n','three\n','a/file','b/file'),('','new\n','/dev/null','b/added')]
 series=[]
 for i,(old,new,src,dst) in enumerate(changes):
  name=str(i)+'.patch';(bundle/'patches'/name).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=src,tofile=dst)))
  series.append({'project':'component','base_commit':head,'patch':name})
 (bundle/'patches/series.json').write_text(json.dumps(series))
 apply=[sys.executable,ci/'apply-reviewed-patches.py','--source',p/'source','--bundle',bundle,'--mode','tracking']
 restore=[sys.executable,ci/'restore-reviewed-tree.py','--source',p/'source','--bundle',bundle]
 run(*apply);run(*apply);assert (repo/'file').read_text()=='three\n' and (repo/'added').read_text()=='new\n'
 run(*restore);assert (repo/'file').read_text()=='one\n' and not (repo/'added').exists()
 git('apply',str(bundle/'patches/0.patch'));run(*apply);assert (repo/'file').read_text()=='three\n'
 (repo/'file').write_text('three\nUNKNOWN\n');run(*restore,ok=False);run(*apply,ok=False);assert 'UNKNOWN' in (repo/'file').read_text()
 (repo/'file').write_text('three\n');(repo/'personal').write_text('retain');run(*restore,ok=False);assert (repo/'personal').read_text()=='retain';(repo/'personal').unlink()
 git('add','file');run(*restore,ok=False);git('reset','HEAD','file');run(*restore)
 git('apply',str(bundle/'patches/0.patch'));git('add','file');git('commit','-m','upstream contains first fix')
 run(*apply);run(*restore);assert (repo/'file').read_text()=='two\n' and not (repo/'added').exists()
print('PASS: multiple same-repo/same-file patches, added files, partial-prefix resume, idempotence, upstream inclusion, unrelated/staged edit refusal')
