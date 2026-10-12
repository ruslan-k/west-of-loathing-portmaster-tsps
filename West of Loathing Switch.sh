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
# A/B (wol-31 -> wol-32): the async GPU pipeline is auto-admitted on this display (EGL_KHR_wait_sync
# present with a separate present context). After the first present the queue path's eglMakeCurrent
# then fails with EGL_BAD_SURFACE (NVN_QUEUE_CONTEXT, detail=0x300d). Block the pipeline for this run;
# WOL_GPU_PIPELINE=1 restores the automatic behaviour.
export T2_GPU_PIPELINE="${WOL_GPU_PIPELINE:-0}"
# A/B (wol-33 -> wol-34): the queue path replaces nvn_device.surface with the 1280x720 window surface
# (single-context mode) and the second submit's eglMakeCurrent fails with EGL_BAD_SURFACE while the
# surface itself still queries alive. The runtime's own pbuffer-producer design renders while bound to
# the 8x8 pbuffer and uses the window surface only for the swap; that mode requires single-context off
# (NVN_SINGLE_CONTEXT_PBUFFER otherwise). WOL_SURFACE_MODE=window restores the previous behaviour.
if [ "${WOL_SURFACE_MODE:-pbuffer}" = pbuffer ]; then
    export COTM_SINGLE_CONTEXT=0 COTM_GAME_PBUFFER=1
fi
# A/B (wol-35, falsified): T2_DISPLAY_BACKEND=fbdev fails at device init with EGL_BAD_DISPLAY (0x3008)
# - SDL/KMSDRM owns the display - so the SDL window stays. The stale-surface problem is fixed in the
# runtime instead (nvn_platform_live_surface): SDL recreates its EGL surface on swap, so the present
# asks SDL for the live surface before binding.
unset NX_PC_BENCH MEGAMAN_OMIT_VIDEOS T2_BOOTCFG_OVERLAY
./wol-horizon
status=$?
printf 'WOL_RUNTIME_EXIT status=%s\n' "$status"
printf '%s\n' "$status" > logs/exit-status.txt
sync
exit "$status"
