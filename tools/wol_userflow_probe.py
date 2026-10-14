import json,os,pathlib,shlex,signal,subprocess,sys,time
port=pathlib.Path('/mnt/SDCARD/Roms/PORTS/wol-switch')
label='userflow-04'
logs=port/'logs'/label
assert not logs.exists(), 'label exists'
logs.mkdir()
launch='/mnt/SDCARD/Roms/PORTS/West of Loathing Switch.sh'
standard='/mnt/SDCARD/Emu/PORTS/../../spruce/scripts/emu/standard_launch.sh'
cmd=pathlib.Path('/tmp/cmd_to_run.sh')
def pids(name):
    result=[]
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if (p/'comm').read_text().strip()==name: result.append(int(p.name))
        except OSError: pass
    return result
def identity(pid):
    p=pathlib.Path('/proc')/str(pid)
    try: return ((p/'comm').read_text().strip(), str((p/'exe').resolve()), (p/'stat').read_text().rsplit(')',1)[1].split()[19])
    except OSError: return None
def capture(name):
    dst=logs/(name+'.png')
    r=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(dst)],capture_output=True,text=True,timeout=20)
    print('KMS',name,r.returncode,r.stdout.strip(),r.stderr.strip(),flush=True)
assert len(pids('MainUI'))==1 and not pids('wol-horizon'), 'device is not idle'
assert not cmd.exists(), 'existing handoff must not be overwritten'
capture('before-menu')
line='chmod a+x '+shlex.quote(standard)+';'+shlex.quote(standard)+' '+shlex.quote(launch)+'\n'
cmd.write_text(line); cmd.chmod(0o755)
subprocess.run(['sh','-n',str(cmd)],check=True)
(logs/'handoff.sh').write_text(line)
owned={}; seen=False; began=None; marks=[40,90,140,170]; done=set(); started=time.monotonic()
try:
    os.kill(pids('MainUI')[0], signal.SIGTERM)
    while time.monotonic()-started<300:
        live=pids('wol-horizon')
        if live:
            for pid in live: owned.setdefault(pid, identity(pid))
            if not seen:
                seen=True; began=time.monotonic()
                print('RUNTIME',live,flush=True)
            elapsed=time.monotonic()-began
            for m in marks:
                if elapsed>=m and m not in done:
                    done.add(m); capture('during-'+str(m))
            if elapsed>=185: break
        elif seen:
            print('RUNTIME_EXITED_AFTER',round(time.monotonic()-began,1),flush=True)
            break
        elif not pids('MainUI') and not seen and time.monotonic()-started>60:
            break
        time.sleep(.5)
    es=port/'exit-status.txt'
    if es.exists(): print('EXIT_STATUS',es.read_text().strip(),flush=True)
    lg=port/'logs'/'latest.log'
    if lg.exists():
        tail=lg.read_text(errors='replace').splitlines()
        stops=[l for l in tail if l.startswith('STOP ') or l.startswith('WOL_RUNTIME_EXIT')]
        print('STOP_LINES',stops[-3:],flush=True)
finally:
    for pid,ident in owned.items():
        if ident and identity(pid)==ident: os.kill(pid,signal.SIGTERM)
    time.sleep(3)
    for pid,ident in owned.items():
        if ident and identity(pid)==ident: os.kill(pid,signal.SIGKILL)
    for _ in range(80):
        if pids('MainUI') and not pids('wol-horizon'): break
        time.sleep(.25)
    if cmd.exists() and cmd.read_text()==line and pids('MainUI'): cmd.unlink()
    time.sleep(1)
    capture('after-menu')
    print('FINAL_STATE',pids('MainUI'),pids('wol-horizon'),flush=True)
print('RUNTIME_SEEN',seen,flush=True)
