#!/usr/bin/env python3
"""Deploy a built wol-horizon to the device: verify hash, back up, swap, read back."""
from pathlib import Path
import hashlib
import subprocess
import sys

name=sys.argv[1]
assert name.startswith('wol-horizon-build-') and '/' not in name
spike=Path('/mnt/external/Hermes/spikes/wol-switch')
elf=spike/name/'wol-horizon'
data=elf.read_bytes()
assert data[:4]==b'\x7fELF'
sha=hashlib.sha256(data).hexdigest()
subprocess.run(['scp','-O',str(elf),'root@192.168.50.135:/mnt/SDCARD/Roms/PORTS/wol-switch/wol-horizon.next'],check=True,timeout=120)
remote='''from pathlib import Path
import hashlib,os,shutil,sys
root=Path('/mnt/SDCARD/Roms/PORTS/wol-switch')
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try: assert (p/'comm').read_text().strip()!='wol-horizon','runtime running'
    except OSError:pass
expected=sys.argv[1]
new=root/'wol-horizon.next'; old=root/'wol-horizon'
assert hashlib.sha256(new.read_bytes()).hexdigest()==expected
oldhash=hashlib.sha256(old.read_bytes()).hexdigest()
bak=root/'backups'/('wol-horizon.'+oldhash[:16]); bak.parent.mkdir(exist_ok=True)
if not bak.exists():shutil.copy2(old,bak)
assert hashlib.sha256(bak.read_bytes()).hexdigest()==oldhash
new.chmod(0o755);new.replace(old)
m=root/'payload.sha256';rows=m.read_text().splitlines()
m.write_text('\\n'.join(expected+'  wol-horizon' if x.endswith('  wol-horizon') else x for x in rows)+'\\n')
os.sync()
print('PREV',oldhash);print('BACKUP',str(bak));print('ACTIVATED',hashlib.sha256(old.read_bytes()).hexdigest())
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','root@192.168.50.135','python3 - '+sha],input=remote,text=True,capture_output=True,timeout=120)
print(r.stdout,r.stderr)
r.check_returncode()
r=subprocess.run(['ssh','-o','BatchMode=yes','root@192.168.50.135','sha256sum /mnt/SDCARD/Roms/PORTS/wol-switch/wol-horizon'],text=True,capture_output=True,timeout=30)
r.check_returncode()
assert r.stdout.split()[0]==sha,('readback mismatch',r.stdout)
print('READBACK_OK',r.stdout.split()[0])
print('DEPLOYED',name,sha)
