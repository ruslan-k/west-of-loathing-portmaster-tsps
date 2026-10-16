#!/usr/bin/env bash
# snap-gpumem.sh <label> — sample mali0/gpu_memory + per-ctx mem_allocs (+ PSS) during a run.
# Series: 30 samples, 6 s apart, starting ~8 s after launch, into /mnt/UDISK/wol-<label>/.
set -uo pipefail
LABEL=${1:?label}
S="ssh -o ControlMaster=no -o ControlPath=none -o BatchMode=yes -o ConnectTimeout=15 tsps"
$S "mkdir -p /mnt/UDISK/wol-$LABEL" 2>/dev/null
sleep 8
for i in $(seq -w 1 30); do
  $S "ts=\$(date +%s); cat /sys/kernel/debug/mali0/gpu_memory 2>/dev/null > /mnt/UDISK/wol-$LABEL/gpumem-$i.txt; echo \"ts=\$ts\" >> /mnt/UDISK/wol-$LABEL/gpumem-$i.txt; for d in /sys/kernel/debug/mali0/ctx/*; do b=\$(basename \$d); cat \$d/mem_allocs 2>/dev/null > /mnt/UDISK/wol-$LABEL/memalloc-$i-\$b.txt; done; pid=\$(pidof wol-horizon 2>/dev/null | awk '{print \$1}'); if [ -n \"\$pid\" ]; then grep -E '^(Pss|SwapPss):' /proc/\$pid/smaps_rollup >> /mnt/UDISK/wol-$LABEL/gpumem-$i.txt 2>/dev/null; fi" 2>/dev/null
  sleep 6
done
echo GPUMEM_SNAP_DONE $LABEL
