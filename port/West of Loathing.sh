#!/bin/sh
GAMEDIR="/mnt/SDCARD/Roms/PORTS/westofloathing"
cd "$GAMEDIR" || exit 1
exec 9>"$GAMEDIR/.run.lock"
flock -n 9 || exit 1
mkdir -p "$GAMEDIR/logs" "$GAMEDIR/home" || exit 1
export HOME="$GAMEDIR/home" XDG_CONFIG_HOME="$GAMEDIR/home/.config"
export LD_LIBRARY_PATH="/usr/trimui/lib:/usr/lib:/lib"
export SDL_VIDEODRIVER=kmsdrm SDL_AUDIODRIVER=alsa UA_DISPLAY=sdl
export UA_PAD_NAME="Xbox Wireless Controller" UA_KEYMAP="start:escape"
export SDL_GAMECONTROLLERCONFIG="0300a3845e0400008e02000014010000,TRIMUI Player1,a:b0,b:b1,x:b2,y:b3,back:b6,guide:b8,start:b7,leftstick:b9,rightstick:b10,leftshoulder:b4,rightshoulder:b5,leftx:a0,lefty:a1,lefttrigger:a2,rightx:a3,righty:a4,righttrigger:a5,dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,platform:Linux,"
case "${WOL_RUN_ID:-latest}" in *[!A-Za-z0-9_-]*|'') exit 1;; esac
exec >"$GAMEDIR/logs/${WOL_RUN_ID:-latest}.log" 2>&1
printf 'WOL_UNITY_RUN id=%s\n' "${WOL_RUN_ID:-latest}"
if [ -n "${WOL_PROBE_SECONDS:-}" ] && [ "$WOL_PROBE_SECONDS" != 0 ]; then
    exec python3 "$GAMEDIR/bounded_run.py" "$GAMEDIR/ua_host" "$GAMEDIR" "$WOL_PROBE_SECONDS"
fi
exec "$GAMEDIR/ua_host" "$GAMEDIR"
