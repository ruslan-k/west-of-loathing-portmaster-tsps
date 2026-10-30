#!/bin/bash
# West of Loathing — SpruceOS launcher (standalone: no PortMaster control.txt needed).
P=/mnt/SDCARD/Roms/PORTS/westofloathing
cd "$P" || exit 1
exec >"$P/log.txt" 2>&1

for pid in $(pgrep -x MainUI); do kill -TERM "$pid"; done
sleep 2

export SDL_VIDEODRIVER=kmsdrm
export SDL_AUDIODRIVER=alsa
export AUDIODEV=plughw:0,0
export UA_AUDIO_SINK=pipe

./ua_host "$P"

pgrep -x MainUI >/dev/null || setsid /mnt/SDCARD/spruce/flip/bin/MainUI >/dev/null 2>&1 &
