"""Validate candidate OTA with matching native target-files and expected public test keys; no device I/O."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,shutil,struct,subprocess,sys,zipfile,time,traceback
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--source',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True)
ap.add_argument('--pipeline-lock-fd',type=int)
args=ap.parse_args();s=args.source.resolve();d=args.candidate.resolve();b=s/'out/host/linux-x86/bin'
inspection=json.loads((d/'ota-inspection.json').read_text());p=d/inspection['filename']
assert p.parent==d and p.name==inspection['filename']
v=d/'offline-validation';v.mkdir(exist_ok=True)
lock_path=d.parents[1]/'pipeline.lock'
if args.pipeline_lock_fd is None:
 lock=lock_path.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
else:
 assert os.fstat(args.pipeline_lock_fd).st_ino==lock_path.stat().st_ino
 fcntl.flock(args.pipeline_lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
if (v/'report.json').exists():
 history=v/'attempt-history'/time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());history.mkdir(parents=True)
 for item in [v/'report.json',*v.glob('*.log')]:shutil.copy2(item,history/item.name)
env={**os.environ,'PATH':str(b)+':'+str(s/'prebuilts/jdk/jdk21/linux-x86/bin')+':'+os.environ['PATH']}
sys.path.insert(0,str(s/'system/update_engine/scripts'));import update_metadata_pb2 as pb
report={'ota':p.name,'sha256':None,'checks':{},'release_accepted':False,'device_written':False}
def save():
 (v/'report.json.tmp').write_text(json.dumps(report,indent=2));(v/'report.json.tmp').replace(v/'report.json')
def run(name,args,cwd=None):
 with (v/(name+'.log')).open('w') as log:
  proc=subprocess.run([str(x) for x in args],env=env,cwd=cwd or s,stdout=log,stderr=subprocess.STDOUT)
 report['checks'][name]={'passed':proc.returncode==0,'exit_code':proc.returncode,'log':name+'.log'};save()
 if proc.returncode:raise RuntimeError(name+' failed; preserve evidence')
def digest(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
try:
 assert p.is_file() and not p.is_symlink()
 report['sha256']=digest(p);assert report['sha256']==inspection['sha256']
 with zipfile.ZipFile(p) as z:
  info=z.getinfo('payload.bin');assert info.compress_type==zipfile.ZIP_STORED
  with p.open('rb') as f:f.seek(info.header_offset);h=f.read(30);n,e=struct.unpack('<HH',h[26:30]);offset=info.header_offset+30+n+e
  with z.open('payload.bin') as f:
   h=f.read(24);assert h[:4]==b'CrAU';m=pb.DeltaArchiveManifest();m.ParseFromString(f.read(struct.unpack('>Q',h[12:20])[0]))
  assert m.minor_version==0 and all(not x.HasField('old_partition_info') for x in m.partitions),'Not a full OTA'
  (v/'ota-embedded-cert.pem').write_bytes(z.read('META-INF/com/android/otacert'))
 cert=s/'build/make/target/product/security/testkey.x509.pem'
 run('certificate-fingerprint',['openssl','x509','-in',cert,'-noout','-fingerprint','-sha256'])
 run('ota-payload-signatures',[b/'check_ota_package_signature',cert,p])
 images=v/'images';images.mkdir(exist_ok=True)
 run('extract-native-payload',[b/'ota_extractor','--payload='+str(p),'--payload_offset='+str(offset),'--output_dir='+str(images)])
 expected={'boot','dtbo','odm','product','recovery','system','system_ext','vbmeta','vbmeta_system','vendor','vendor_boot','vendor_dlkm'}
 assert {x.partition_name for x in m.partitions}==expected,'Unexpected partition set'
 capacities={'super':12884901888,'boot_a':100663296,'boot_b':100663296,'dtbo_a':25165824,'dtbo_b':25165824,'recovery_a':104857600,'recovery_b':104857600,'vendor_boot_a':100663296,'vendor_boot_b':100663296,'vbmeta_a':65536,'vbmeta_b':65536,'vbmeta_system_a':65536,'vbmeta_system_b':65536}
 misc=dict(x.split('=',1) for x in (s/'out/target/product/asphalt/misc_info.txt').read_text().splitlines() if '=' in x)
 parts=[]
 for part in m.partitions:
  name=part.partition_name;image=images/(name+'.img');actual=digest(image)
  assert image.stat().st_size==part.new_partition_info.size and actual==part.new_partition_info.hash.hex(),name+' payload hash mismatch'
  if name+'_a' in capacities:
   assert all(image.stat().st_size<=capacities[name+'_'+slot] for slot in ['a','b']),name+' exceeds archived physical capacity'
  # OTA is generated from target_files/IMAGES. Product-root boot.img is an
  # earlier intermediate and can differ after native target-files packaging.
  built=s/'out/target/product/asphalt/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files/IMAGES'/(name+'.img')
  with built.open('rb') as f:magic=f.read(4)
  expanded=v/('expanded-'+name+'.img')
  if magic==b'\x3a\xff\x26\xed':
   run('expand-'+name,[b/'simg2img',built,expanded]);compare=expanded
  else:compare=built
  assert digest(compare)==actual,name+' disagrees with build image'
  if compare==expanded:expanded.unlink()
  parts.append({'name':name,'bytes':image.stat().st_size,'sha256':actual,'payload_manifest_match':True,'build_image_match':True,'archived_capacity_bytes':capacities.get(name+'_a')})
 dynamic=[]
 for group in m.dynamic_partition_metadata.groups:
  used=sum(x.new_partition_info.size for x in m.partitions if x.partition_name in group.partition_names)
  assert used<=group.size
  assert group.size==int(misc['super_'+group.name+'_group_size'])
  assert 2*group.size+2*4194304<=capacities['super'],'A/B groups plus conservative metadata allowance exceed archived super'
  dynamic.append({'name':group.name,'used_bytes':used,'group_capacity_bytes':group.size,'two_slots_plus_metadata_bytes':2*group.size+2*4194304,'archived_super_bytes':capacities['super']})
 report['partitions']=parts;report['dynamic_groups']=dynamic;report['image_comparison_source']='Native OTA input target_files/IMAGES (not product-root intermediates)';report['capacity_source']='Archived physical capacity snapshot; current device state still requires read-only preflight'
 report['checks']['partition_hashes_and_capacity']={'passed':True,'partitions':len(parts)};save()
 run('avb-chain-public-key',[b/'avbtool','extract_public_key','--key',s/'external/avb/test/data/testkey_rsa2048.pem','--output',v/'testkey2048.avbpubkey'])
 # Explicitly bind the two chain descriptors, then verify each child against
 # its RSA2048 key. This avbtool version propagates --key to followed children;
 # using a root RSA4096 key with --follow_chain_partitions would mis-test them.
 run('avb-root',[b/'avbtool','verify_image','--image',images/'vbmeta.img','--key',s/'external/avb/test/data/testkey_rsa4096.pem','--expected_chain_partition','recovery:1:'+str(v/'testkey2048.avbpubkey'),'--expected_chain_partition','vbmeta_system:2:'+str(v/'testkey2048.avbpubkey')],cwd=images)
 run('avb-system',[b/'avbtool','verify_image','--image',images/'vbmeta_system.img','--key',s/'external/avb/test/data/testkey_rsa2048.pem'],cwd=images)
 run('avb-recovery',[b/'avbtool','verify_image','--image',images/'recovery.img','--key',s/'external/avb/test/data/testkey_rsa2048.pem'],cwd=images)
 for name in ['vbmeta','vbmeta_system','recovery']:
  run('avb-info-'+name,[b/'avbtool','info_image','--image',images/(name+'.img')])
 target=s/'out/target/product/asphalt/obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files'
 run('vintf',[b/'check_target_files_vintf',target])
 report['security']={'ota_signing':'AOSP public testkey','avb_root_key':'AOSP public RSA4096 test key','avb_chain_key':'AOSP public RSA2048 test key','avb_flags':misc['avb_vbmeta_args'],'vintf_enforce':misc['vintf_enforce'],'not_production_private_signing':True}
 report['offline_validation']='passed';report['remaining']=['Current device A/B, ABL, partition metadata and free space','Current OTA trust/installed versions, GApps and Magisk state','Fresh private-data and exact boot rollback backup','User approval before flashing and subsequent hardware test','Separate private-key migration for stable OTA promotion']
 save();print(json.dumps(report,indent=2))
except Exception as e:
 report['offline_validation']='failed';report['error']=str(e);save();traceback.print_exc();raise
