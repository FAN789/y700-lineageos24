"""Select the exact packaged Lineage build, ignoring stale hard-link aliases."""
from pathlib import Path
import argparse, re, zipfile

def properties(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))

def select(product_out, reference):
    out=product_out.resolve()
    target=out/'obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files'
    system=properties(target/'SYSTEM/build.prop')
    product=properties(target/'PRODUCT/etc/build.prop')
    version=product['ro.lineage.version']
    assert re.fullmatch(r'24\.0-\d{8}-[A-Za-z0-9_.-]+-asphalt',version),'Unexpected packaged version'
    ota=out/('lineage-'+version+'.zip')
    assert ota.is_file() and not ota.is_symlink() and ota.resolve().parent==out,'Missing canonical OTA'
    assert ota.stat().st_mtime_ns>reference.stat().st_mtime_ns,'Canonical OTA predates this build'
    with zipfile.ZipFile(ota) as z:
        meta=dict(line.split('=',1) for line in z.read('META-INF/com/android/metadata').decode().splitlines() if '=' in line)
    assert meta['post-build-incremental']==system['ro.build.version.incremental'],'OTA/build identity mismatch'
    assert meta['ota-type']=='AB' and 'TB320FC' in meta['pre-device'].split(','),'Unexpected OTA target'
    return ota

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--product-out',type=Path,required=True);p.add_argument('--newer-than',type=Path,required=True)
    a=p.parse_args();print(select(a.product_out,a.newer_than))
