"""Trust-anchor regressions before any OTA is read or native tool is run."""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, tempfile

validator=Path(__file__).with_name('validate-native.py')
with tempfile.TemporaryDirectory() as td:
    root=Path(td);keys=root/'keys';keys.mkdir()
    for name in ['ota.pem','root.pem','chain.pem']:(keys/name).write_text('public fixture '+name)
    policy={'schema':1,'purpose':'y700-private-release'}
    for field,name in [('ota_certificate','ota.pem'),('avb_root_public_key','root.pem'),('avb_chain_public_key','chain.pem')]:
        policy[field]={'file':name,'sha256':hashlib.sha256((keys/name).read_bytes()).hexdigest()}
    def probe(value):
        (keys/'policy.json').write_text(json.dumps(value))
        return subprocess.run([sys.executable,str(validator),'--source',str(root/'source'),'--candidate',str(root/'candidate'),
                               '--signing-policy',str(keys/'policy.json')],capture_output=True,text=True)
    valid=probe(policy)
    assert valid.returncode!=0 and 'ota-inspection.json' in valid.stderr,'Valid anchors should reach OTA loading'
    changed=copy.deepcopy(policy);changed['ota_certificate']['sha256']='0'*64
    assert 'Public trust anchor mismatch' in probe(changed).stderr
    changed=copy.deepcopy(policy);changed['avb_root_public_key']['file']='../outside.pem';(root/'outside.pem').write_text('outside')
    rejected=probe(changed);assert rejected.returncode!=0 and 'ota-inspection.json' not in rejected.stderr
    changed=copy.deepcopy(policy);changed['purpose']='arbitrary-self-signed'
    rejected=probe(changed);assert rejected.returncode!=0 and 'ota-inspection.json' not in rejected.stderr
    (keys/'link.pem').symlink_to(keys/'ota.pem')
    changed=copy.deepcopy(policy);changed['ota_certificate']['file']='link.pem'
    rejected=probe(changed)
    assert rejected.returncode!=0 and 'ota-inspection.json' not in rejected.stderr,'Symlink trust anchor must be rejected'
print('PASS: pinned key hashes, path boundaries, explicit release policy and symlink rejection')
