#!/bin/bash
# Experimental WoL Switch runtime. Launch only through Spruce/PortMaster principal flow.
GAMEDIR=/mnt/SDCARD/Roms/PORTS/wol-switch
cd "$GAMEDIR" || exit 1
mkdir -p logs save-laboratory
LOG="$GAMEDIR/logs/latest.log"
exec >"$LOG" 2>&1
printf 'WOL_LAUNCH native-horizon diagnostic-budget=%ss shader-catalogue=absent\n' "${WOL_PROBE_SECONDS:-0}"
printf 'WOL_BUILD_ID sha256=%s\n' "$(sha256sum ./wol-horizon 2>/dev/null | cut -d ' ' -f1)"
# Spruce normally offlines the cluster to which this recovered runtime pins its threads.
# The runtime pins its threads to the cluster Spruce normally offlines. Remember each file's original
# state and restore it on exit so a run leaves the device exactly as it found it (run 42 left 0-7 online).
CPU_RESTORE=""
for c in 0 1 2 3; do
    p="/sys/devices/system/cpu/cpu${c}/online"
    [ -e "$p" ] || continue
    previous=$(<"$p")
    CPU_RESTORE="$CPU_RESTORE $c:$previous"
    chmod u+w "$p" 2>/dev/null || true
    if [ "$previous" = 0 ]; then printf 1 >"$p" || true; fi
done
restore_cpu() {
    for entry in $CPU_RESTORE; do
        c=${entry%%:*}; want=${entry##*:}
        p="/sys/devices/system/cpu/cpu${c}/online"
        [ -e "$p" ] || continue
        printf '%s' "$want" >"$p" 2>/dev/null || true
    done
}
trap restore_cpu EXIT
export HOME="$GAMEDIR"
export SDL_VIDEODRIVER=kmsdrm SDL_AUDIODRIVER=alsa
# SDL installs crash handlers that catch SIGSEGV and re-raise it themselves, which hides the
# original fault from this runtime's handler (observed si_code=SI_TKILL inside libpthread raise).
# The runtime's own fault reporting must stay authoritative.
export SDL_NO_SIGNAL_HANDLERS=1
export SDL_GAMECONTROLLERCONFIG='0300a3845e0400008e02000014010000,TRIMUI Player1,a:b0,b:b1,back:b6,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b8,leftshoulder:b4,leftstick:b9,lefttrigger:a2,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b10,righttrigger:a5,rightx:a3,righty:a4,start:b7,x:b2,y:b3,platform:Linux,'
export COTM_RUN_ID=$(date +%s)
# A/B (wol-39 -> wol-40): the load hit the memory floor after 32 frames while staging the 191 MiB RomFS
# read. The staging peak may be transient, so let the load finish inside the same bounded run:
# WOL_PROBE_SECONDS=35 restores the shorter diagnostic budget.
# 2026-10-14 (the "crash"): the 900 s diagnostic budget stopped a real play session with
# STOP status=TIME_LIMIT (exit 22). The packaged runtime treats an explicit 0 as "no alarm"
# (loader.c: "Explicit zero cancels the diagnostic alarm for the packaged runtime") - the default
# is now 0, and every bounded diagnostic passes WOL_PROBE_SECONDS=<seconds> explicitly.
export MEGAMAN_PROBE_SECONDS="${WOL_PROBE_SECONDS:-0}"
# 2026-10-14 (performance): the not-quiet path runs full-texture GPU->CPU readback probes per
# unresolved draw plus the per-call IPC trace - measured at ~5 presents/s for this title. WOL_QUIET=1
# is the runtime's speed path ("removes the per-draw texture content probing from the hot path");
# the shader substitution, banks and counters stay intact. Diagnostics pass WOL_QUIET=0 explicitly.
export WOL_QUIET="${WOL_QUIET:-1}"
# The 64/32 MiB floors are bounded diagnostics (they demonstrated 120-600 presents and swap engagement).
# 2026-10-14 (menu launch, production path): measured floor trips during the RomFS load staging -
# floor 140 tripped at ~130 MiB available (detail=0x82), 64 at ~55 (detail=0x37), 32 at ~31
# (detail=0x1f - less than 1 MiB of margin). All day the bounded harness ran the full load plus
# hours of presents at floor 20 without a single floor stop, so the available-memory dip stays
# above 20 but below 32; 20 is the only demonstrated-survivable value on this device.
export T2_MEMORY_FLOOR_MIB="${WOL_MEMORY_FLOOR_MIB:-20}"
export COTM_BLACK_LIMIT="${WOL_BLACK_LIMIT:-4000}"
export WOL_PAIR_CHECK="${WOL_PAIR_CHECK:-1}"

# Run 43 measured the guest compactor at zero benefit for this title (compressions=0, saved=0.0,
# scope=alias_physical only), so it stays OFF by default: the periodic scans and page-fault hooks are
# cost without gain. WOL_GUEST_ZRAM=1 re-enables it for a deliberate A/B.
export T2_GUEST_ZRAM="${WOL_GUEST_ZRAM:-0}"
export T2_GZRAM_TARGET_MIB="${WOL_GZRAM_TARGET_MIB:-400}" T2_GZRAM_STATS_MS=1000 T2_GZRAM_POOLS=0
export MEGAMAN_LAZY_ZERO=0 T2_LAZY_MESH=0 T2_IMAGE_FILE_MAP=1
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
