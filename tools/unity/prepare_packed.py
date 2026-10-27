#!/usr/bin/env python3
"""Pack already-converted owner data with the pinned Unity toolchain; never consume the input."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

PIN = '913debc122b8234a3db56939a4728d9438972ce2'
HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('workspace', type=Path, help='owner-local converter workspace described in README.md')
    ap.add_argument('output', type=Path, help='new output directory (must not already exist)')
    args = ap.parse_args()
    work, out = args.workspace.resolve(), args.output.resolve()
    pu = work / 'portmaster-unity'
    mono = work / 'cuphead-runtime/cuphead/setup64/mono64'
    extra = work / 'classlibs-extra'
    dotnet = os.environ.get('DOTNET', 'dotnet')
    actual = subprocess.check_output(['git', '-C', str(pu), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != PIN:
        ap.error(f'converter must be pinned to {PIN}, got {actual}')
    required = [work / 'data/globalgamemanagers', work / 'data/Managed/Assembly-CSharp.dll',
                work / 'player/player.json', work / 'asmpatch/asmpatch.dll', mono / 'classlibs/mscorlib.dll',
                mono / 'etc/mono/config', extra / 'System.IO.Compression.dll',
                extra / 'System.Runtime.Serialization.dll', extra / 'System.ServiceModel.Internals.dll']
    for p in required:
        if not p.is_file():
            ap.error(f'missing prerequisite: {p}')
    out.mkdir(parents=True, exist_ok=False)
    sdk = subprocess.check_output([dotnet, '--list-sdks'], text=True).splitlines()[-1]
    match = re.fullmatch(r'(\S+) \[(.+)\]', sdk)
    if not match:
        raise RuntimeError('cannot locate Roslyn from dotnet --list-sdks')
    csc = Path(match[2]) / match[1] / 'Roslyn/bincore/csc.dll'
    refs = ['-reference:' + str(mono / 'classlibs' / n) for n in ['mscorlib.dll', 'System.dll']]
    refs += ['-reference:' + str(extra / 'System.IO.Compression.dll')]
    subprocess.run([dotnet, str(csc), '-nologo', '-noconfig', '-nostdlib+', '-target:library',
                    '-out:' + str(out / 'WoLPackedAssets.dll'), *refs, str(HERE / 'WoLPackedAssets.cs')], check=True)
    subprocess.run([dotnet, 'build', str(HERE / 'patcher/Patcher.csproj'), '-c', 'Release',
                    '-o', str(out / 'patcher'), '--nologo'], check=True)
    subprocess.run([dotnet, str(work / 'asmpatch/asmpatch.dll'), '--only=rewired-android',
                    str(work / 'data/Managed'), str(out / 'rewired')], check=True)
    subprocess.run([dotnet, str(out / 'patcher/Patcher.dll'), str(out / 'rewired'), str(out / 'patched'),
                    str(out / 'WoLPackedAssets.dll'), str(work / 'data/Managed')], check=True)
    command = [sys.executable, '-m', 'pmunity', 'android-data', '--src', str(work / 'data'),
               '--pkg', str(work / 'player'), '--out', str(out / 'android'), '--name', 'WestOfLoathing',
               '--package', 'com.ruslank.westofloathing', '--mono64', '--streaming-assets', 'obb',
               '--drop-missing-assembly', 'Kartridge.dll', '--managed-file', str(out / 'patched/Assembly-CSharp.dll'),
               '--managed-file', str(out / 'WoLPackedAssets.dll'), '--mono-etc', str(mono / 'etc'),
               '--pack', 'all', '--verify-bundles', '-1']
    for directory in [mono / 'classlibs', extra]:
        for dll in sorted(directory.glob('*.dll')):
            command += ['--managed-file', str(dll)]
    subprocess.run(command, cwd=pu, env=dict(os.environ, PYTHONPATH=str(pu / 'convert')), check=True)
    print('PACKED_OWNER_DATA', out / 'android/zip')


if __name__ == '__main__':
    main()
