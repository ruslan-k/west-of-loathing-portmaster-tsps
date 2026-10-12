#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
"${AARCH64_CC:-aarch64-linux-gnu-gcc}" -static -O2 -Wall -Wextra -Werror \
    wol_native_probe.c -o wol-native-probe
