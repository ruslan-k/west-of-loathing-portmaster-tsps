#!/usr/bin/env python3
"""pl:u shared font service: source contract for the WoL fail-closed stop fix.

The 2026-10-15 battle-scene run stopped with
  GET_SERVICE name=pl:u -> STOP status=UNIMPLEMENTED_SERVICE (exit 20)
because sm_lookup had no endpoint for the shared font manager that this SDK
initializes on its first platform-font UI path. The runtime now answers the
service instead of stopping. This test pins the source contract; the decisive
behaviour evidence is the device log line PL_SERVICE command=... replacing the
stop on a real run.
"""
from pathlib import Path
import sys

n = Path(sys.argv[1])
src = (n / 'ipc.h').read_text()

# 1. The endpoint exists and pl:u is mapped to it (narrow: exact 8-byte name).
assert 'EP_PL_STUB' in src, 'missing EP_PL_STUB endpoint'
assert 'if(!memcmp(name,"pl:u\\0\\0\\0\\0",8))found=EP_PL_STUB;' in src, 'pl:u not mapped to EP_PL_STUB'

# 2. The mapping lives inside sm_lookup, before its return, so the fail-closed
#    UNIMPLEMENTED_SERVICE stop is never reached for a permitted pl:u request.
lookup = src.split('static enum endpoint sm_lookup(const uint8_t *name) {', 1)[1].split('\n}', 1)[0]
assert 'found=EP_PL_STUB' in lookup, 'pl:u mapping outside sm_lookup'

# 3. Every pl request is logged sampled (first payload bytes) and answered: command 1
#    (the polled load state) with u32 1 = loaded, default-on; other commands succeed
#    with zeroed output buffers. No stop(...) on this endpoint.
handler = src.split('if(endpoint==EP_PL_STUB) {', 1)[1].split('\n    }\n', 1)[0]
for needle in ('"PL_SERVICE command="', 'req.command', 'req.data_size',
               'pl_trace_count<8 || !(pl_trace_count&255)',
               '"WOL_PL_CMD1_REPLY"',
               'uint32_t v=1;ipc_reply(buffer,req.token,0,&v,4,0,req.domain);return;',
               'memset((void *)(uintptr_t)req.outputs[i].address,0,req.outputs[i].size)',
               'ipc_reply(buffer,req.token,0,NULL,0,0,req.domain);return;'):
    assert needle in handler, 'EP_PL_STUB handler missing ' + needle
assert 'stop(' not in handler, 'EP_PL_STUB handler must not stop'
# 3b. Command 4 hands out a real EP_SHARED handle for the 0x1100000 font region; reply
#     shape switchable by WOL_PL_CMD4_REPLY (default: u32 handle in reply data).
for needle in ('shared_create(0x1100000ULL,1,pc)',
               'session_new(EP_SHARED,pc)',
               'session_get(shm_handle,pc)->initialized=pl_shared_id',
               '"WOL_PL_CMD4_REPLY"',
               'if(pl_cmd4_mode==0){ipc_reply(buffer,req.token,0,&shm_handle,4,0,req.domain);return;}',
               '(o&&!strcmp(o,"data"))?0:2;',
               'ipc_reply(buffer,req.token,0,NULL,0,shm_handle,0);return;'):
    assert needle in handler, 'EP_PL_STUB command 4 missing ' + needle
mem = (n / 'memory.h').read_text()
assert 'size>(32U<<20)' in mem, 'shared region bound must allow the 0x1100000 font region'
ld = (n / 'loader.c').read_text()
assert 'if(!r[0]){r[0]=0xe01;' in ld, 'svc 0x13 must answer handle 0 with a survivable error'

# 4. The UNIMPLEMENTED_SERVICE stop stays for services genuinely not in the map.
assert 'stop("UNIMPLEMENTED_SERVICE",pc,req.command,20);' in src, 'fail-closed stop for unknown services must remain'

print('PASS pl:u service contract: mapped to EP_PL_STUB, logged, zeroed outputs, success reply, fail-closed stop retained for unknown services')
