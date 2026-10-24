#!/usr/bin/env python3
"""Inspect A/B transport integrity; promotion needs independent signed acceptance."""
import argparse,base64,hashlib,json,re,struct,zipfile
from pathlib import Path

def inspect(path):
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None,'ZIP CRC failure'
  assert len(z.namelist())==len(set(z.namelist())),'Duplicate ZIP entries'
  meta=dict(x.split('=',1) for x in z.read('META-INF/com/android/metadata').decode().splitlines() if '=' in x)
  assert meta['ota-type']=='AB' and 'TB320FC' in meta['pre-device'].split(','),'Wrong target'
  assert meta['post-sdk-level']=='37','Wrong Android SDK'
  assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',meta['post-security-patch-level'])
  props=dict(x.split('=',1) for x in z.read('payload_properties.txt').decode().splitlines() if '=' in x)
  with z.open('payload.bin') as f:
   head=f.read(24);assert head[:4]==b'CrAU' and struct.unpack('>Q',head[4:12])[0]==2,'Unknown payload format'
   # update_engine GetMetadataSize()/METADATA_HASH excludes the signature.
   # Releasetools' synthetic payload_metadata.bin range includes it.
   size_meta=24+struct.unpack('>Q',head[12:20])[0]
   size_meta_range=size_meta+struct.unpack('>I',head[20:24])[0]
   assert int(props['METADATA_SIZE'])==size_meta
   h=hashlib.sha256(head);mh=hashlib.sha256(head);pos=len(head)
   while chunk:=f.read(8*1024*1024):
    h.update(chunk)
    if pos<size_meta:mh.update(chunk[:size_meta-pos])
    pos+=len(chunk)
  assert pos==int(props['FILE_SIZE']) and base64.b64encode(h.digest()).decode()==props['FILE_HASH'],'Payload mismatch'
  assert base64.b64encode(mh.digest()).decode()==props['METADATA_HASH'],'Metadata mismatch'
  # Validate every actual streaming range, including synthetic payload_metadata.bin.
  with path.open('rb') as raw:
   offsets={}
   for item in z.infolist():
    raw.seek(item.header_offset);hdr=raw.read(30);n,e=struct.unpack('<HH',hdr[26:30]);offsets[item.filename]=(item.header_offset+30+n+e,item.file_size,item.compress_type)
   for spec in meta['ota-property-files'].strip().split(','):
    name,offset,length=spec.split(':');offset,length=int(offset),int(length)
    if name=='payload_metadata.bin':assert (offset,length)==(offsets['payload.bin'][0],size_meta_range)
    else:
     actual=next((v for k,v in offsets.items() if k==name or k.rsplit('/',1)[-1]==name),None)
     assert actual and actual==(offset,length,zipfile.ZIP_STORED),'Invalid streaming range: '+name
 with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 return {'filename':path.name,'sha256':sha,'size':path.stat().st_size,'metadata':meta,'transport_integrity':'passed','release_accepted':False,'remaining':['payload partition reconstruction and capacity','OTA/payload signatures and AVB','SELinux/VINTF and hardware acceptance','signing migration and root persistence']}

def main():
 p=argparse.ArgumentParser();p.add_argument('operation',choices=['inspect','feed']);p.add_argument('ota',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--acceptance',type=Path);p.add_argument('--url');a=p.parse_args();r=inspect(a.ota)
 if a.operation=='feed':
  assert a.acceptance and a.url,'Promotion requires acceptance and URL'
  acceptance=json.loads(a.acceptance.read_text());assert acceptance['sha256']==r['sha256']
  for gate in ['private_release_signatures','payload_partitions_capacity','avb','selinux_vintf','hardware','key_migration','root_persistence']:
   assert acceptance['checks'].get(gate) is True,'Missing acceptance: '+gate
  assert a.url.startswith('https://github.com/FAN789/y700-lineageos24/releases/download/') and a.url.endswith('/'+r['filename'])
  m=r['metadata'];r=[{'datetime':int(m['post-timestamp']),'version':'24.0','type':'UNOFFICIAL','files':[{'filename':r['filename'],'os_patch_level':m['post-security-patch-level'],'os_sdk_level':37,'ota_property_files':m['ota-property-files'],'sha256':r['sha256'],'size':r['size'],'url':a.url}]}]
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
