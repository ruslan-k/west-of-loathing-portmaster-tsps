# Device-side principal-flow diagnostic. Run via ssh python3 - < this file.
import pathlib,os,signal,time,subprocess
port=pathlib.Path('/mnt/SDCARD/Roms/PORTS/wol-switch')
launch=pathlib.Path('/mnt/SDCARD/Roms/PORTS/West of Loathing.sh')
cmd=pathlib.Path('/tmp/cmd_to_run.sh')
def pids(name):
    found=[]
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if (p/'comm').read_text().strip()==name: found.append(int(p.name))
        except OSError: pass
    return found
assert len(pids('MainUI'))==1,'device is not in the verified menu state'
assert not pids('wol-horizon'),'runtime already running'
assert not cmd.exists(),'existing principal handoff must not be overwritten'
logs=port/'logs'; logs.mkdir(exist_ok=True)
subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(logs/'before-menu.png')],check=True)
line='sync; echo 10 > /proc/sys/vm/swappiness; echo 300 > /proc/sys/vm/vfs_cache_pressure; echo 3 > /proc/sys/vm/drop_caches; chmod a+x "/mnt/SDCARD/Emu/PORTS/../../spruce/scripts/emu/standard_launch.sh";WOL_PROBE_SECONDS="${WOL_TEST_SECONDS:-7200}" WOL_MEMORY_FLOOR_MIB="${WOL_TEST_FLOOR:-20}" WOL_QUIET="${WOL_TEST_QUIET:-1}" WOL_PRESENT_TEST="${WOL_TEST_PRESENT:-0}" WOL_PAIR_TEST="${WOL_TEST_PAIR:-0}" WOL_FS_TESTTEX="${WOL_TEST_FSTEX:-0}" WOL_PAIR_MATH="${WOL_TEST_PAIR_MATH:-1}" WOL_VS_TRIVIAL="${WOL_TEST_TRIVIAL:-0}" WOL_COHERENCE="${WOL_TEST_COHERENCE:-1}" WOL_DUMP="${WOL_TEST_DUMP:-1}" COTM_VIDEO_CAPTURE_PERIOD="${WOL_TEST_CAP_PERIOD:-300}" WOL_PAIR_PRIM="${WOL_TEST_PRIM:-strip}" WOL_F191_UV="${WOL_TEST_UV:-xy}" WOL_COMPOSITE_PROBE="${WOL_TEST_COMPOSITE_PROBE:-0}" WOL_PROBE_TARGET="${WOL_TEST_PROBE_TARGET:-457}" "/mnt/SDCARD/Emu/PORTS/../../spruce/scripts/emu/standard_launch.sh" "'+str(launch)+'"\n'
cmd.write_text(line); cmd.chmod(0o755)
subprocess.run(['sh','-n',str(cmd)],check=True)
os.kill(pids('MainUI')[0],signal.SIGTERM)
seen=False
for i in range(20000):
    time.sleep(0.1)
    live=pids('wol-horizon')
    if live and not seen:
        seen=True; print('RUNTIME_LIVE',live,flush=True)
        subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(logs/'during-run.png')],check=False)
    if i>=30 and not live and pids('MainUI'):
        print('MENU_RETURNED',pids('MainUI'),'runtime_seen',seen,flush=True); break
else:
    # Only this test's exact comm; never terminate an unrelated game or menu supervisor.
    for pid in pids('wol-horizon'): os.kill(pid,signal.SIGTERM)
    time.sleep(3)
    for pid in pids('wol-horizon'): os.kill(pid,signal.SIGKILL)
    time.sleep(3)
    subprocess.run(['sh','-c','echo 100 > /proc/sys/vm/swappiness; echo 100 > /proc/sys/vm/vfs_cache_pressure'],check=False)
    print('BOUNDED_TEST_CLEANUP',pids('MainUI'),pids('wol-horizon'),flush=True)
if cmd.exists() and cmd.read_text()==line: cmd.unlink()
time.sleep(2)
subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(logs/'after-menu.png')],check=False)
log=logs/'latest.log'
if log.exists(): print(log.read_text(errors='replace')[-20000:])
print('FINAL_STATE',pids('MainUI'),pids('wol-horizon'),flush=True)
