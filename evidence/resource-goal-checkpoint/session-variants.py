from pathlib import Path
import os,sys,time,subprocess,signal,shlex,hashlib,json,socket,struct,re,shutil
root=Path('/mnt/SDCARD/Roms/PORTS/wol-switch')
out=Path('/mnt/UDISK/wol-goal-20261015');out.mkdir(exist_ok=True)
def pids(comm):
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            if (p/'comm').read_text().strip()==comm:result.append(int(p.name))
        except OSError:pass
    return result
def identity(pid):
    p=Path('/proc')/str(pid)
    try:return ((p/'comm').read_text(),(p/'stat').read_text().rsplit(')',1)[1].split()[19])
    except OSError:return None
def cap(name):
    for _ in range(6):
        result=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(out/(name+'.png'))],timeout=25)
        if result.returncode==0:return
        time.sleep(2)
    raise RuntimeError('no framebuffer after six captures')
def stop():
    for pid in pids('wol-horizon'):
        ident=identity(pid);print('STOP_EXACT',pid,ident,flush=True)
        os.kill(pid,signal.SIGTERM)
        for _ in range(40):
            if identity(pid)!=ident:break
            time.sleep(.25)
        if identity(pid)==ident:os.kill(pid,signal.SIGKILL)
    for _ in range(100):
        if pids('MainUI') and not pids('wol-horizon'):break
        time.sleep(.3)
    assert not pids('wol-horizon') and len(pids('MainUI'))==1,('not idle',pids('MainUI'),pids('wol-horizon'))
    cap('restored-menu')
    print('IDLE',pids('MainUI'),flush=True)
mode=sys.argv[1]
if mode=='stop':
    stop()
elif mode=='start':
    label=sys.argv[2]
    stop()
    save=out/(label+'-saves-before')
    if not save.exists():shutil.copytree(root/'save-laboratory',save)
    log=root/'logs/latest.log'
    if log.exists():
        shutil.copyfile(log, out/(label+'-previous.log'))
    cmd=Path('/tmp/cmd_to_run.sh')
    if cmd.exists():
        old=cmd.read_text();assert 'West of Loathing Switch.sh' in old,('foreign handoff',old)
        (out/(label+'-previous-handoff.txt')).write_text(old);cmd.unlink()
    assert sys.argv[3] in ('0','1')
    env=dict(WOL_PROBE_SECONDS='900',COTM_INPUT_DIAGNOSTIC='1',WOL_RECT_TRACE='off',MOMO_FRAME_CLOCK='1',WOL_DRAW_TRACE=sys.argv[3])
    if len(sys.argv)>4:
        extra=json.loads(sys.argv[4]);assert all(k.startswith(('WOL_','COTM_','T2_','MEGAMAN_')) for k in extra);env.update(extra)
    standard='/mnt/SDCARD/Emu/PORTS/../../spruce/scripts/emu/standard_launch.sh'
    launch='/mnt/SDCARD/Roms/PORTS/West of Loathing Switch.sh'
    line='env '+' '.join(shlex.quote(k+'='+v) for k,v in env.items())+' '+shlex.quote(standard)+' '+shlex.quote(launch)+'\n'
    cmd.write_text(line);cmd.chmod(0o755);subprocess.run(['sh','-n',str(cmd)],check=True)
    os.kill(pids('MainUI')[0],signal.SIGTERM)
    for _ in range(100):
        if pids('wol-horizon'):break
        time.sleep(.3)
    assert len(pids('wol-horizon'))==1
    pid=pids('wol-horizon')[0];ident=identity(pid)
    actual=dict(e.split('=',1) for e in (Path('/proc')/str(pid)/'environ').read_bytes().decode().strip('\0').split('\0') if '=' in e)
    for k,v in env.items():assert actual.get(k)==v,(k,v,actual.get(k))
    (out/'session.json').write_text(json.dumps(dict(label=label,pid=pid,identity=ident,env=env)))
    print('STARTED',label,pid,flush=True)
    time.sleep(65)
    assert identity(pid)==ident,('runtime ended',pid)
    cap(label+'-title')
    print('ALIVE',pid,'ONLINE',Path('/sys/devices/system/cpu/online').read_text(),flush=True)
elif mode=='press':
    state=json.loads((out/'session.json').read_text());pid=state['pid']
    assert identity(pid)==tuple(state['identity'])
    log=root/'logs/latest.log'
    with log.open('rb') as f:head=f.read(30000)
    sock=re.search(rb'HID_DIAGNOSTIC_SOCKET path=(\S+)',head).group(1).decode()
    bits=int(sys.argv[2],0);stick=int(sys.argv[3],0) if len(sys.argv)>3 else 0
    assert bits&0xc00!=0xc00
    s=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);s.sendto(struct.pack('<QII',bits,int(sys.argv[6]) if len(sys.argv)>6 else 180,stick),sock)
    print('SENT',pid,sock,bits,stick,flush=True)
    time.sleep(int(sys.argv[4]) if len(sys.argv)>4 else 12)
    assert identity(pid)==tuple(state['identity'])
    cap(state['label']+'-'+sys.argv[5] if len(sys.argv)>5 else state['label']+'-after')
    print('ALIVE',pid,flush=True)
else:raise ValueError(mode)
