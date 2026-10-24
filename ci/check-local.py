#!/usr/bin/env python3
"""Exercise patch safety and OTA rejection without firmware builds."""
from pathlib import Path
import base64,hashlib,json,os,struct,subprocess,sys,tempfile,zipfile
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
 device=root/'device';device.mkdir();run('git','-C',str(device),'init');run('git','-C',str(device),'config','core.autocrlf','false')
 # The pinned upstream device makefile has no trailing newline.
 (device/'lineage_asphalt.mk').write_bytes(b'placeholder\n'*28+b'# GMS\nPRODUCT_GMS_CLIENTID_BASE := android-lenovo')
 endpoint=str(bundle/'ci/0006-asphalt-private-channel-endpoint.patch')
 run('git','-C',str(device),'apply','--check',endpoint);run('git','-C',str(device),'apply',endpoint)
 assert b'lineage.updater.uri=https://' in (device/'lineage_asphalt.mk').read_bytes()
 # Nonzero signature length is essential: property metadata excludes it,
 # whereas the streaming metadata range includes it (native Android behavior).
 manifest=b'fixture-manifest';signature=b'fixture-signature'
 payload=b'CrAU'+struct.pack('>QQI',2,len(manifest),len(signature))+manifest+signature+b'body'
 metadata_size=24+len(manifest)
 h64=lambda data:base64.b64encode(hashlib.sha256(data).digest()).decode()
 def fixture(path,wrong_size=False,wrong_hash=False):
  props=('FILE_HASH='+h64(payload)+'\nFILE_SIZE='+str(len(payload))+'\nMETADATA_HASH='+h64(payload[:metadata_size] if not wrong_hash else b'wrong')+'\nMETADATA_SIZE='+str(metadata_size+(len(signature) if wrong_size else 0))+'\n').encode()
  def write(meta):
   with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
    z.writestr('META-INF/com/android/metadata',meta);z.writestr('payload.bin',payload);z.writestr('payload_properties.txt',props)
  write(b' '*2048)
  with zipfile.ZipFile(path) as z:
   with path.open('rb') as raw:
    offsets={}
    for item in z.infolist():
     raw.seek(item.header_offset);header=raw.read(30);n,e=struct.unpack('<HH',header[26:30]);offsets[item.filename]=item.header_offset+30+n+e
  offset=offsets['payload.bin']
  meta=('ota-type=AB\npre-device=asphalt,TB320FC\npost-sdk-level=37\npost-security-patch-level=2026-10-01\npost-timestamp=1792804343\nota-property-files=payload_metadata.bin:'+str(offset)+':'+str(metadata_size+len(signature))+',payload.bin:'+str(offset)+':'+str(len(payload))+'\n').encode()
  assert len(meta)<=2048;write(meta+b' '*(2048-len(meta)))
 for name,wrong_size,wrong_hash in [('valid',False,False),('wrong-size',True,False),('wrong-hash',False,True)]:
  path=root/(name+'.zip');fixture(path,wrong_size,wrong_hash)
  run(sys.executable,str(bundle/'ci/ota-feed.py'),'inspect',str(path),'--output',str(root/(name+'.json')),ok=name=='valid')
print('PASS: patch safety, wrong-device rejection, upstream EOF, signed-metadata size/hash and streaming range')
