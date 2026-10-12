#!/bin/bash
# Experimental WoL Switch runtime. Launch only through Spruce/PortMaster principal flow.
GAMEDIR=/mnt/SDCARD/Roms/PORTS/wol-switch
cd "$GAMEDIR" || exit 1
mkdir -p logs save-laboratory
LOG="$GAMEDIR/logs/latest.log"
exec >"$LOG" 2>&1
printf 'WOL_LAUNCH native-horizon diagnostic-budget=35s shader-catalogue=absent\n'
# Spruce normally offlines the cluster to which this recovered runtime pins its threads.
for c in 0 1 2 3; do
    p="/sys/devices/system/cpu/cpu${c}/online"
    [ -e "$p" ] || continue
    chmod a+w "$p" 2>/dev/null || true
    if [ "$(<"$p")" = 0 ]; then printf 1 >"$p" || true; fi
    chmod a-w "$p" 2>/dev/null || true
done
export HOME="$GAMEDIR"
export SDL_VIDEODRIVER=kmsdrm SDL_AUDIODRIVER=alsa
# SDL installs crash handlers that catch SIGSEGV and re-raise it themselves, which hides the
# original fault from this runtime's handler (observed si_code=SI_TKILL inside libpthread raise).
# The runtime's own fault reporting must stay authoritative.
export SDL_NO_SIGNAL_HANDLERS=1
export SDL_GAMECONTROLLERCONFIG='0300a3845e0400008e02000014010000,TRIMUI Player1,a:b0,b:b1,back:b6,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b8,leftshoulder:b4,leftstick:b9,lefttrigger:a2,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b10,righttrigger:a5,rightx:a3,righty:a4,start:b7,x:b2,y:b3,platform:Linux,'
export COTM_RUN_ID=$(date +%s)
export MEGAMAN_PROBE_SECONDS=35
export MEGAMAN_LAZY_ZERO=0 T2_GUEST_ZRAM=0 T2_LAZY_MESH=0 T2_IMAGE_FILE_MAP=1
export T2_SAVE_DIR="$GAMEDIR/save-laboratory"
unset NX_PC_BENCH MEGAMAN_OMIT_VIDEOS T2_BOOTCFG_OVERLAY
./wol-horizon
status=$?
printf 'WOL_RUNTIME_EXIT status=%s\n' "$status"
printf '%s\n' "$status" > logs/exit-status.txt
sync
exit "$status"
