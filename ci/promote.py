#!/usr/bin/env python3
"""Promote an existing, independently accepted GitHub Release asset."""
import hashlib,json,os,re,subprocess,sys,urllib.request
from pathlib import Path
repo='FAN789/y700-lineageos24'
tag=os.environ['RELEASE_TAG'];filename=os.environ['OTA_FILENAME'];sha=os.environ['OTA_SHA256'].lower()
assert re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',tag)
assert re.fullmatch(r'lineage-24\.0-[A-Za-z0-9_.-]+-asphalt\.zip',filename)
assert re.fullmatch(r'[0-9a-f]{64}',sha)
acceptance=Path('ota/acceptance')/(sha+'.json')
assert acceptance.is_file(),'No reviewed acceptance record for this exact OTA'
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'Y700-OTA-Promotion','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
def api(path,method='GET',data=None):
 req=urllib.request.Request('https://api.github.com'+path,headers=headers,method=method,data=None if data is None else json.dumps(data).encode())
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
release=api('/repos/'+repo+'/releases/tags/'+tag)
assets=[a for a in release['assets'] if a['name']==filename];assert len(assets)==1
asset=assets[0];assert asset.get('digest')=='sha256:'+sha,'Release digest mismatch'
url='https://github.com/'+repo+'/releases/download/'+tag+'/'+filename
assert asset['browser_download_url']==url
path=Path(os.environ['RUNNER_TEMP'])/filename
with urllib.request.urlopen(url,timeout=120) as src,path.open('wb') as dst:
 while chunk:=src.read(8*1024*1024):dst.write(chunk)
with path.open('rb') as src:assert hashlib.file_digest(src,'sha256').hexdigest()==sha
assert path.stat().st_size==asset['size']
subprocess.run([sys.executable,'ci/ota-feed.py','feed',str(path),'--acceptance',str(acceptance),'--url',url,'--output','ota/asphalt.next.json'],check=True)
previous=Path('ota/asphalt.json').read_bytes();history=Path('ota/history');history.mkdir(exist_ok=True)
(history/(hashlib.sha256(previous).hexdigest()+'.json')).write_bytes(previous)
Path('ota/asphalt.next.json').replace('ota/asphalt.json')
api('/repos/'+repo+'/releases/'+str(release['id']),'PATCH',{'prerelease':False})
print('Exact accepted release ready for feed commit:',sha)
