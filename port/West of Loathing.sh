#!/bin/bash
# West of Loathing — PortMaster launcher for the native Switch runtime (TSPS / SpruceOS, aarch64).
#
# Layout expected next to this script:
#   port/West of Loathing.sh        (this file)
#   port/wol-switch/wol-horizon     (runtime binary, GPL-3.0, built from ../../runtime + ../../build_horizon.sh)
#   port/wol-switch/*.seg           (owner-extracted NSO segments — NOT distributed)
#   port/wol-switch/wol-romfs.section (owner-extracted RomFS section — NOT distributed)
#
# The game files are proprietary: this repo ships no ROM, NSO, RomFS, save or shader payload.
# See ../../evidence/release-720/README.md for what was accepted on hardware.

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
if [ -d "/opt/system/Tools/PortMaster/" ]; then
    controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
    controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
    controlfolder="$XDG_DATA_HOME/PortMaster"
else
    controlfolder="/roms/ports/PortMaster"
fi

[ -f "$controlfolder/control.txt" ] && source "$controlfolder/control.txt"
type get_controls >/dev/null 2>&1 && get_controls
[ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"

# Port layout preference: if this launcher sits next to its own wol-switch directory (as in port/),
# use that. Otherwise follow PortMaster's $directory, then the plain TSPS path.
SELF_DIR=$(cd "$(dirname "$0")" && pwd)
if [ -d "$SELF_DIR/wol-switch" ]; then
    GAMEDIR="$SELF_DIR/wol-switch"
elif [ -n "${directory:-}" ] && [ -d "/$directory/ports/wol-switch" ]; then
    GAMEDIR="/$directory/ports/wol-switch"
else
    GAMEDIR="${WOL_GAMEDIR:-/mnt/SDCARD/Roms/PORTS/wol-switch}"
fi
cd "$GAMEDIR" || { echo "Game directory not found: $GAMEDIR"; sleep 3; exit 1; }

missing=""
for f in wol-horizon main.text.seg main.rodata.seg main.data.seg \
         rtld.text.seg rtld.rodata.seg rtld.data.seg \
         subsdk0.text.seg subsdk0.rodata.seg subsdk0.data.seg \
         sdk.text.seg sdk.rodata.seg sdk.data.seg wol-romfs.section; do
    [ -f "$f" ] || missing="$missing $f"
done
if [ -n "$missing" ]; then
    echo "Missing owner game files:$missing"
    echo "Extract the segments and RomFS section from YOUR copy of the game (see port/README.md)."
    sleep 6
    exit 1
fi

mkdir -p logs save-laboratory
exec >"$GAMEDIR/logs/latest.log" 2>&1
printf 'WOL_LAUNCH native-horizon portmaster-launcher budget=%ss\n' "${WOL_PROBE_SECONDS:-0}"
printf 'WOL_BUILD_ID sha256=%s\n' "$(sha256sum ./wol-horizon 2>/dev/null | cut -d ' ' -f1)"

# Spruce/PortMaster normally offlines the cluster this runtime pins its threads to. Remember each
# CPU's original state and restore it on exit, so a run leaves the device exactly as it found it.
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
# SDL installs crash handlers that hide the original fault from the runtime's own reporter.
export SDL_NO_SIGNAL_HANDLERS=1
export SDL_GAMECONTROLLERCONFIG='0300a3845e0400008e02000014010000,TRIMUI Player1,a:b0,b:b1,back:b6,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b8,leftshoulder:b4,leftstick:b9,lefttrigger:a2,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b10,righttrigger:a5,rightx:a3,righty:a4,start:b7,x:b2,y:b3,platform:Linux,'
export COTM_RUN_ID=$(date +%s)
export MEGAMAN_PROBE_SECONDS="${WOL_PROBE_SECONDS:-0}"

# --- Operational profile (owner-accepted 2026-10-19) -------------------------------------------------
# Quiet release: no diagnostic receipts, no per-frame trace, no dumps next to the game.
export AW_RELEASE="${AW_RELEASE:-1}"
export WOL_QUIET="${WOL_QUIET:-1}"
# Video sampling only until the first image proof, then explicit captures only.
export T2_READBACK_OFF="${T2_READBACK_OFF:-2}"
export COTM_PRESENT_READBACK_60="${COTM_PRESENT_READBACK_60:-0}"
export COTM_READBACK_PERIOD="${COTM_READBACK_PERIOD:-120}"
# 720 UpRender size-only profile: the game's 3D targets render 1280x720, the presenter scales to the
# 720p panel. This is the accepted default; set WOL_UPRENDER_720=0 for the old 1080-class profile.
export WOL_UPRENDER_720="${WOL_UPRENDER_720:-1}"
# Native precision and refresh path validated on hardware.
export WOL_PACKED4444="${WOL_PACKED4444:-1}"
export WOL_RGBA8_COPY="${WOL_RGBA8_COPY:-1}"
export WOL_CPU_OFFSET="${WOL_CPU_OFFSET:-4}"
export WOL_TOP_UV="${WOL_TOP_UV:-raw}"
export WOL_TOP_RAWID="${WOL_TOP_RAWID:-none}"
export WOL_TOP_SMART="${WOL_TOP_SMART:-0}"
export WOL_F191_UV="${WOL_F191_UV:-none}"
export WOL_F191_NOFOLDID="${WOL_F191_NOFOLDID:-none}"
export WOL_PAIR_STENCIL="${WOL_PAIR_STENCIL:-1}"
export WOL_PAIR_CHECK="${WOL_PAIR_CHECK:-0}"
export WOL_RECT_TRACE="${WOL_RECT_TRACE:-off}"
export T2_MEMORY_FLOOR_MIB="${WOL_MEMORY_FLOOR_MIB:-20}"
export COTM_BLACK_LIMIT="${WOL_BLACK_LIMIT:-4000}"
export T2_GUEST_ZRAM="${WOL_GUEST_ZRAM:-0}"
export MEGAMAN_LAZY_ZERO=0 T2_LAZY_MESH=0 T2_IMAGE_FILE_MAP=1
export T2_SAVE_DIR="$GAMEDIR/save-laboratory"
export T2_GPU_PIPELINE="${T2_GPU_PIPELINE:-0}"
if [ "${WOL_SURFACE_MODE:-pbuffer}" = pbuffer ]; then
    export COTM_SINGLE_CONTEXT=0 COTM_GAME_PBUFFER=1
fi
unset NX_PC_BENCH MEGAMAN_OMIT_VIDEOS T2_BOOTCFG_OVERLAY

./wol-horizon
status=$?
printf 'WOL_RUNTIME_EXIT status=%s\n' "$status"
printf '%s\n' "$status" > logs/exit-status.txt
sync
exit "$status"
