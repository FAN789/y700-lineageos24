#!/usr/bin/env python3
"""Compile and execute the reviewed C/GPIO negative-case and compatibility matrix."""
from pathlib import Path
import subprocess,tempfile,json
ci=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='y700-ucsi-matrix-') as td:
 binary=Path(td)/'matrix'
 subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ci/'fixtures/ucsi-mux-source-derived.c'),'-o',str(binary)],check=True)
 r=json.loads(subprocess.check_output([str(binary)],text=True));assert r['passed'] and r['cases']==10752
 print(json.dumps(r))
