#!/usr/bin/env python3
"""Stage only validated firmware in an unpublished release, never device backups."""
from pathlib import Path
import hashlib,http.client,json,os,re,urllib.parse,urllib.request
repo='FAN789/y700-lineageos24';run=os.environ['CANDIDATE_RUN'];assert re.fullmatch(r'[0-9]{8}T[0-9]{6}Z',run)
c=Path('/home/builder/y700-lineage24/candidates')/run
report=json.loads((c/'offline-validation/report.json').read_text());assert report['offline_validation']=='passed'
assert all(x['passed'] for x in report['checks'].values())
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'Y700-Private-Firmware-Staging','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
def api(path,method='GET',data=None):
 r=urllib.request.Request('https://api.github.com'+path,headers=headers,method=method,data=None if data is None else json.dumps(data).encode())
 with urllib.request.urlopen(r,timeout=60) as f:return json.load(f)
tag='candidate-'+run.lower()
matches=[r for r in api('/repos/'+repo+'/releases?per_page=100') if r['tag_name']==tag]
assert len(matches)<=1
if matches:release=matches[0]
else:release=api('/repos/'+repo+'/releases','POST',{'tag_name':tag,'target_commitish':'main','name':'Y700 offline-validated candidate '+run,'body':'UNPUBLISHED transport staging. Offline validation passed; device acceptance and installation approval are pending. No device backups or personal data. This draft must not be published or promoted automatically.','draft':True,'prerelease':True})
assert release['draft'] is True,'Refuse to upload to a published release'
files=[c/report['ota']]+[c/'offline-validation/images'/(n+'.img') for n in ['boot','dtbo','vendor_boot','recovery','vbmeta','vbmeta_system']]
assert files[0].parent==c and files[0].name==report['ota']
assets=api('/repos/'+repo+'/releases/'+str(release['id'])+'/assets');done=[]
for p in files:
 assert p.is_file() and not p.is_symlink()
 with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 if p.suffix=='.zip':assert sha==report['sha256']
 old=[a for a in assets if a['name']==p.name];assert len(old)<=1
 if old:
  asset=old[0];assert asset.get('digest')=='sha256:'+sha and asset['size']==p.stat().st_size
 else:
  conn=http.client.HTTPSConnection('uploads.github.com',timeout=3600)
  conn.putrequest('POST','/repos/'+repo+'/releases/'+str(release['id'])+'/assets?name='+urllib.parse.quote(p.name,safe=''))
  for key,value in {**headers,'Content-Type':'application/octet-stream','Content-Length':str(p.stat().st_size)}.items():conn.putheader(key,value)
  conn.endheaders()
  with p.open('rb') as f:
   while chunk:=f.read(1024*1024):conn.send(chunk)
  response=conn.getresponse();raw=response.read();assert response.status==201,'Draft asset upload failed: '+str(response.status)
  asset=json.loads(raw);conn.close();assert asset.get('digest')=='sha256:'+sha
 done.append({'name':p.name,'size':p.stat().st_size,'sha256':sha,'asset_id':asset['id'],'api_url':asset['url']})
 (c/'draft-staging.json').write_text(json.dumps({'draft':True,'release_id':release['id'],'tag':tag,'assets':done},indent=2))
 print('Staged unpublished firmware asset:',p.name,flush=True)
assert api('/repos/'+repo+'/releases/'+str(release['id']))['draft'] is True
print('Unpublished firmware staging complete; no OTA feed change or device action.')
