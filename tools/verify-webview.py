#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the exact upstream arm64 WebView LFS object and verify it."""
import argparse,hashlib,subprocess,zipfile
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--check-only',action='store_true')
    args=ap.parse_args();repo=args.source.resolve()/'external/chromium-webview/prebuilt/arm64';apk=repo/'webview.apk'
    pointer=subprocess.check_output(['git','-C',str(repo),'show','HEAD:webview.apk'])
    if not pointer.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        raise SystemExit('Expected an upstream LFS pointer; inspect this revision manually.')
    fields=dict(line.split(' ',1) for line in pointer.decode().splitlines()[1:])
    expected=fields['oid'].removeprefix('sha256:');size=int(fields['size'])
    def valid():
        if not apk.is_file() or apk.stat().st_size != size:return False
        with apk.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==expected
    if not valid():
        if args.check_only:raise SystemExit('LFS object is missing or mismatched.')
        subprocess.run(['git','-C',str(repo),'lfs','install','--local'],check=True)
        subprocess.run(['git','-C',str(repo),'lfs','pull','github','--include=webview.apk','--exclude='],check=True)
    if not valid():raise SystemExit('WebView hash or size mismatch.')
    with zipfile.ZipFile(apk) as z:
        if z.testzip() is not None or 'AndroidManifest.xml' not in z.namelist():raise SystemExit('Invalid WebView APK.')
    print('Pinned WebView SHA256, size and ZIP integrity passed.')
if __name__=='__main__':main()
