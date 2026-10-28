"""Read regular files from boot-image newc ramdisks without extracting paths."""
from pathlib import PurePosixPath,Path
import gzip,stat,subprocess

def entries(raw):
 offset=0
 while offset<len(raw):
  while offset<len(raw) and raw[offset]==0:offset+=1
  if offset==len(raw):break
  h=raw[offset:offset+110];assert len(h)==110 and h[:6] in [b'070701',b'070702']
  fields=[int(h[6+8*i:14+8*i],16) for i in range(13)];size,namesize=fields[6],fields[11];assert 0<namesize<65536
  name=raw[offset+110:offset+110+namesize];assert name.endswith(b'\0');path=PurePosixPath(name[:-1].decode());assert not path.is_absolute() and '..' not in path.parts
  start=(offset+110+namesize+3)&~3;assert start+size<=len(raw)
  if stat.S_ISREG(fields[1]):yield str(path),raw[start:start+size]
  offset=(start+size+3)&~3

def read(path):
 raw=Path(path).read_bytes()
 if raw[:2]==b'\x1f\x8b':return gzip.decompress(raw)
 if raw[:6] in [b'070701',b'070702']:return raw
 return subprocess.check_output(['lz4','-dc',str(path)])
