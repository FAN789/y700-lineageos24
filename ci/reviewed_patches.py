"""Plan exact reviewed patch prefixes in isolated indexes; never reset unknown edits."""
from pathlib import Path
import json,os,subprocess,tempfile

def git(repo,*args,env=None,check=True):
 r=subprocess.run(['git','-C',str(repo),*args],env=env,capture_output=True)
 if check:assert r.returncode==0,r.stderr.decode(errors='replace')
 return r

def index_env(path):return {**os.environ,'GIT_INDEX_FILE':str(path)}
def diff(repo,env):return git(repo,'diff','--cached','--no-ext-diff','--no-textconv','--binary','--full-index','HEAD',env=env).stdout

def snapshot(repo,allowed):
 assert git(repo,'diff','--cached','--quiet','HEAD',check=False).returncode==0,'Staged edits must be preserved: '+str(repo)
 changed=set(git(repo,'diff','--name-only','-z','HEAD').stdout.decode().strip('\0').split('\0'))-{''}
 unknown=set(git(repo,'ls-files','--others','--exclude-standard','-z').stdout.decode().strip('\0').split('\0'))-{''}
 assert (changed|unknown)<=allowed,'Unreviewed paths: '+str(repo)
 with tempfile.TemporaryDirectory(prefix='y700-actual-index-') as td:
  env=index_env(Path(td)/'index');git(repo,'read-tree','HEAD',env=env);git(repo,'add','-u',env=env)
  if unknown:git(repo,'add','--',*sorted(unknown),env=env)
  return diff(repo,env)

def plan(bundle,source,mode=None):
 series=json.loads((bundle/'patches/series.json').read_text())
 if (bundle/'ci/patches.json').exists():series+=json.loads((bundle/'ci/patches.json').read_text())
 groups={}
 for item in series:groups.setdefault(item['project'],[]).append(item)
 plans=[]
 for project,items in groups.items():
  repo=source/project
  if mode is None and not (repo/'.git').exists():continue
  head=git(repo,'rev-parse','HEAD').stdout.decode().strip()
  patches=[];allowed=set()
  for item in items:
   if mode=='baseline':assert head==item['base_commit'],project
   elif mode=='tracking':assert git(repo,'merge-base','--is-ancestor',item['base_commit'],'HEAD',check=False).returncode==0,'Upstream ancestry changed: '+project
   patch=(bundle/'patches'/item['patch']).resolve();patches.append(patch)
   for line in patch.read_text().splitlines():
    if line.startswith(('+++ b/','--- a/')):
     name=line[6:];assert not Path(name).is_absolute() and '..' not in Path(name).parts
     allowed.add(name)
  before=snapshot(repo,allowed);states=[b''];active=[]
  with tempfile.TemporaryDirectory(prefix='y700-model-index-') as td:
   env=index_env(Path(td)/'index');git(repo,'read-tree','HEAD',env=env)
   for patch in patches:
    if git(repo,'apply','--cached','--reverse','--check',str(patch),env=env,check=False).returncode==0:continue
    git(repo,'apply','--cached','--check',str(patch),env=env)
    git(repo,'apply','--cached',str(patch),env=env);active.append(patch);states.append(diff(repo,env))
  assert before in states,'Known patch paths contain unknown content: '+project
  count=states.index(before)
  plans.append({'repo':repo,'allowed':allowed,'before':before,'applied':active[:count],'pending':active[count:],'final':states[-1]})
 return plans
