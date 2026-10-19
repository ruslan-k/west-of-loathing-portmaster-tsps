#!/usr/bin/env python3
"""Owner-device principal helper: start/press only; cleanup belongs to the PID/start-time owner."""
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
mode=sys.argv[1]
if mode=='start':
    label=sys.argv[2]
    assert label.replace('-','').isalnum(), 'simple label required'
    assert not pids('wol-horizon') and len(pids('MainUI'))==1, 'refuse non-idle start; never stop an unowned game'
    save=out/(label+'-saves-before')
    if not save.exists():shutil.copytree(root/'save-laboratory',save)
    log=root/'logs/latest.log'
    if log.exists():
        shutil.copyfile(log, out/(label+'-previous.log'))
    cmd=Path('/tmp/cmd_to_run.sh')
    if cmd.exists():
        old=cmd.read_text();assert 'West of Loathing Switch.sh' in old,('foreign handoff',old)
        (out/(label+'-previous-handoff.txt')).write_text(old);cmd.unlink()
    assert sys.argv[3] in ('0','1','normal')
    env=dict(WOL_PROBE_SECONDS='900',COTM_INPUT_DIAGNOSTIC='1',WOL_RECT_TRACE='off',MOMO_FRAME_CLOCK='1',WOL_DRAW_TRACE=sys.argv[3])
    if os.environ.get('WOL_PL_CMD4_REPLY'):env['WOL_PL_CMD4_REPLY']=os.environ['WOL_PL_CMD4_REPLY']
    if os.environ.get('WOL_PL_CMD1_REPLY'):env['WOL_PL_CMD1_REPLY']=os.environ['WOL_PL_CMD1_REPLY']
    if os.environ.get('WOL_DISPLAY_MAX'):env['WOL_DISPLAY_MAX']=os.environ['WOL_DISPLAY_MAX']
    if os.environ.get('WOL_NVN_ASTC'):env['WOL_NVN_ASTC']=os.environ['WOL_NVN_ASTC']
    if os.environ.get('COTM_STREAM_VBO'):env['COTM_STREAM_VBO']=os.environ['COTM_STREAM_VBO']
    if os.environ.get('WOL_PAIR_RING'):env['WOL_PAIR_RING']=os.environ['WOL_PAIR_RING']
    if os.environ.get('AW_PROFILE'):env['AW_PROFILE']=os.environ['AW_PROFILE']
    if os.environ.get('COTM_GUEST_PROFILE'):env['COTM_GUEST_PROFILE']=os.environ['COTM_GUEST_PROFILE']
    if os.environ.get('WOL_COPY_GPU'):env['WOL_COPY_GPU']=os.environ['WOL_COPY_GPU']
    if os.environ.get('WOL_COPY_GPU_FLIP'):env['WOL_COPY_GPU_FLIP']=os.environ['WOL_COPY_GPU_FLIP']
    if os.environ.get('WOL_REFRESH_DIRECT'):env['WOL_REFRESH_DIRECT']=os.environ['WOL_REFRESH_DIRECT']
    if os.environ.get('COTM_REPLAY_PHASES'):env['COTM_REPLAY_PHASES']=os.environ['COTM_REPLAY_PHASES']
    if os.environ.get('COTM_POINTER_FAST'):env['COTM_POINTER_FAST']=os.environ['COTM_POINTER_FAST']
    if os.environ.get('WOL_GPU_RESIDENCY'):env['WOL_GPU_RESIDENCY']=os.environ['WOL_GPU_RESIDENCY']
    if os.environ.get('WOL_VTX_CENSUS'):env['WOL_VTX_CENSUS']=os.environ['WOL_VTX_CENSUS']
    if os.environ.get('MEGAMAN_OTHER_TRAP_PROFILE'):env['MEGAMAN_OTHER_TRAP_PROFILE']=os.environ['MEGAMAN_OTHER_TRAP_PROFILE']
    if os.environ.get('T2P_SLOW_MS'):env['T2P_SLOW_MS']=os.environ['T2P_SLOW_MS']
    if os.environ.get('COTM_PRESENT_READBACK_60'):env['COTM_PRESENT_READBACK_60']=os.environ['COTM_PRESENT_READBACK_60']
    if os.environ.get('COTM_READBACK_PERIOD'):env['COTM_READBACK_PERIOD']=os.environ['COTM_READBACK_PERIOD']
    if os.environ.get('WOL_CPU_OFFSET'):env['WOL_CPU_OFFSET']=os.environ['WOL_CPU_OFFSET']
    if os.environ.get('WOL_COPYTRACE'):env['WOL_COPYTRACE']=os.environ['WOL_COPYTRACE']
    if os.environ.get('WOL_ASTC_CACHE'):env['WOL_ASTC_CACHE']=os.environ['WOL_ASTC_CACHE']
    if os.environ.get('COTM_RESOURCE_LOOKUP_CACHE'):env['COTM_RESOURCE_LOOKUP_CACHE']=os.environ['COTM_RESOURCE_LOOKUP_CACHE']
    if os.environ.get('WOL_SAMPLE_SPLIT'):env['WOL_SAMPLE_SPLIT']=os.environ['WOL_SAMPLE_SPLIT']
    if os.environ.get('WOL_COPY_AUDIT'):env['WOL_COPY_AUDIT']=os.environ['WOL_COPY_AUDIT']
    if os.environ.get('WOL_BC_WRITE_TRACE'):env['WOL_BC_WRITE_TRACE']=os.environ['WOL_BC_WRITE_TRACE']
    if os.environ.get('WOL_ROMFS_LIFETIME'):env['WOL_ROMFS_LIFETIME']=os.environ['WOL_ROMFS_LIFETIME']
    if os.environ.get('WOL_ALLOC_TRACE'):env['WOL_ALLOC_TRACE']=os.environ['WOL_ALLOC_TRACE']
    if os.environ.get('WOL_ASTC_POSTCOPY'):env['WOL_ASTC_POSTCOPY']=os.environ['WOL_ASTC_POSTCOPY']
    if os.environ.get('WOL_PBO_UPLOAD'):env['WOL_PBO_UPLOAD']=os.environ['WOL_PBO_UPLOAD']
    if os.environ.get('WOL_UPLOAD_TIMING'):env['WOL_UPLOAD_TIMING']=os.environ['WOL_UPLOAD_TIMING']
    if os.environ.get('WOL_ASTC_POSTCOPY_ID'):env['WOL_ASTC_POSTCOPY_ID']=os.environ['WOL_ASTC_POSTCOPY_ID']
    # Host-allocation attribution (2026-10-19): the LD_PRELOAD shim logs host mmap/malloc
    # requests >= WOL_HOSTMMAP_MIN with caller frames. Default OFF: only forwarded when the
    # invoking environment sets LD_PRELOAD explicitly.
    if os.environ.get('LD_PRELOAD'):env['LD_PRELOAD']=os.environ['LD_PRELOAD']
    # Guest TransferMemory copy mode (2026-10-19): the runtime's sparse backing copy keeps
    # zero pages uncommitted; forwarded explicitly because the generic loop only carries WOL_*.
    if os.environ.get('T2_TRANSFER_SPARSE_COPY'):env['T2_TRANSFER_SPARSE_COPY']=os.environ['T2_TRANSFER_SPARSE_COPY']
    # Screen-rect draw filter: prints every draw whose transformed bbox intersects the rect,
    # which is how a single UI region (e.g. the guide's location list) is inspected.
    # Generic WOL_* passthrough (2026-10-16): A/B runs need the runtime's own gates
    # (WOL_F191_UV, WOL_F191_REAL, WOL_TOP_DRAFT, WOL_PAIR2_DRAFT, ...) without editing
    # this harness for every switch. Anything already set above wins.
    for _k,_v in os.environ.items():
        if _k.startswith('WOL_') and _k not in env:
            env[_k]=_v
    if os.environ.get('WOL_RECT_TRACE') and os.environ['WOL_RECT_TRACE']!='off':
        env['WOL_RECT_TRACE']=os.environ['WOL_RECT_TRACE']
        if os.environ.get('WOL_RECT_TRACE_LIMIT'):env['WOL_RECT_TRACE_LIMIT']=os.environ['WOL_RECT_TRACE_LIMIT']
    if sys.argv[3]=='normal':env={}
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
    # A fixed 65-second delay is not a title-ready gate under allocation tracing.
    # Inspect the known static title sign before sending CONTINUE; keep each score.
    from wol_screen_gate import wait_for_title
    readiness=[]
    def record_readiness(observed):
        readiness.append(observed)
        (out/(label+'-title-readiness.json')).write_text(json.dumps(readiness,indent=2)+'\n')
    observed=wait_for_title(lambda:cap(label+'-title'),out/(label+'-title.png'),
                            lambda:identity(pid)==ident,record_readiness)
    print('TITLE_READY',json.dumps(observed),flush=True)
    print('ALIVE',pid,'ONLINE',Path('/sys/devices/system/cpu/online').read_text(),flush=True)
elif mode=='press':
    state=json.loads((out/'session.json').read_text());pid=state['pid']
    assert identity(pid)==tuple(state['identity'])
    log=root/'logs/latest.log'
    with log.open('rb') as f:head=f.read(30000)
    match=re.search(rb'HID_DIAGNOSTIC_SOCKET path=(\S+)',head)
    if not match:raise RuntimeError('fresh runtime has no diagnostic socket receipt')
    sock=match.group(1).decode()
    bits=int(sys.argv[2],0);stick=int(sys.argv[3],0) if len(sys.argv)>3 else 0
    hold=int(sys.argv[6]) if len(sys.argv)>6 else 180
    assert 0<=bits<1<<64 and 0<=stick<1<<32 and 1<=hold<=2000
    assert bits&0xc00!=0xc00
    action=sys.argv[5] if len(sys.argv)>5 else 'after'
    assert action.replace('-','').isalnum()
    receipt=dict(pid=pid,start_ticks=state['identity'][1],buttons=hex(bits),stick=stick,hold_ms=hold,
                 sent_begin_ns=time.monotonic_ns(),physical_input_verified=False,
                 caveat='Diagnostic request timing only; runtime delivery and real KMS/scene change remain separate checks.')
    s=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);s.sendto(struct.pack('<QII',bits,hold,stick),sock)
    s.close();receipt['sent_end_ns']=time.monotonic_ns()
    print('SENT',pid,sock,bits,stick,flush=True)
    time.sleep(int(sys.argv[4]) if len(sys.argv)>4 else 12)
    assert identity(pid)==tuple(state['identity'])
    receipt['capture_begin_ns']=time.monotonic_ns()
    cap(state['label']+'-'+action)
    receipt['capture_end_ns']=time.monotonic_ns()
    (out/(state['label']+'-'+action+'-input.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print('ALIVE',pid,flush=True)
else:raise ValueError(mode)
