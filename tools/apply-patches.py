#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check fixed source revisions and apply only the reviewed release patches."""
import argparse,json,subprocess
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--check-only',action='store_true')
    args=ap.parse_args(); root=args.source.resolve()
    bundle=Path(__file__).resolve().parents[1]
    pending=[]
    for entry in json.loads((bundle/'patches/series.json').read_text()):
        repo=root/entry['project']; patch=bundle/'patches'/entry['patch']
        def git(*cmd,check=True):
            return subprocess.run(['git','-C',str(repo),*cmd],check=check,capture_output=True,text=True)
        head=git('rev-parse','HEAD').stdout.strip()
        if head != entry['base_commit']:
            raise SystemExit('Unexpected source revision: '+entry['project'])
        if git('apply','--reverse','--check',str(patch),check=False).returncode == 0:
            print('Already present:',entry['project']);continue
        if git('status','--porcelain').stdout.strip():
            raise SystemExit('Unreviewed working changes: '+entry['project'])
        result=git('apply','--check',str(patch),check=False)
        if result.returncode:
            raise SystemExit('Patch check failed: '+entry['patch']+'\n'+result.stderr)
        pending.append((repo,patch))
    if args.check_only:
        print('All patches passed preflight; no changes made.');return
    for repo,patch in pending:
        subprocess.run(['git','-C',str(repo),'apply',str(patch)],check=True)
        subprocess.run(['git','-C',str(repo),'diff','--check'],check=True)
        print('Applied:',patch.name)
if __name__=='__main__':main()
