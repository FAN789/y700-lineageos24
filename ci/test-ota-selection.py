"""Regression: old dated names can be hard links to the newly written OTA."""
from pathlib import Path
import importlib.util, os, tempfile, zipfile
spec=importlib.util.spec_from_file_location('select_ota',Path(__file__).with_name('select-ota.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    out=Path(td);target=out/'obj/PACKAGING/target_files_intermediates/lineage_asphalt-target_files'
    (target/'SYSTEM').mkdir(parents=True);(target/'PRODUCT/etc').mkdir(parents=True)
    (target/'SYSTEM/build.prop').write_text('ro.build.version.incremental=123456\n')
    (target/'PRODUCT/etc/build.prop').write_text('ro.lineage.version=24.0-20261027-UNOFFICIAL-asphalt\n')
    ref=out/'manifest.xml';ref.write_text('fixture');os.utime(ref,ns=(100,100))
    canonical=out/'lineage-24.0-20261027-UNOFFICIAL-asphalt.zip'
    def write(incremental):
        with zipfile.ZipFile(canonical,'w') as z:z.writestr('META-INF/com/android/metadata','ota-type=AB\npre-device=asphalt,TB320FC\npost-build-incremental='+incremental+'\n')
    write('123456');os.link(canonical,out/'lineage-24.0-20261024-UNOFFICIAL-asphalt.zip')
    assert m.select(out,ref)==canonical
    write('wrong')
    try:m.select(out,ref)
    except AssertionError:pass
    else:raise AssertionError('Wrong incremental identity accepted')
    write('123456');os.utime(canonical,ns=(1,1))
    try:m.select(out,ref)
    except AssertionError:pass
    else:raise AssertionError('Stale artifact accepted')
print('PASS: canonical packaged identity, stale hard-link aliases and stale/wrong OTA rejection')
