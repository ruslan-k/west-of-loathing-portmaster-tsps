#!/usr/bin/env python3
"""Exercise the actual fail-closed full-image host-upload cache helper."""
import subprocess,tempfile,unittest
from pathlib import Path
from test_wol_memory_handheld import added_header

class UploadGuardContract(unittest.TestCase):
    def test_upload_commit_writes_aliases_context_and_reuse(self):
        code='''#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
'''+added_header('wol_copy_equal.h')+added_header('wol_upload_guard.h')+r'''
int main(void) {
    struct wol_upload_guard s={0};uint8_t p[8]={0};
    struct wol_copy_equal_key k={.object=1,.id=1,.pool=2,.address=0x1000,.bytes=8,.name=3,.context=4};
    assert(!wol_upload_guard_prepare(&s,&k,p));
    assert(!wol_upload_guard_prepare(&s,&k,p)); /* no successful upload yet */
    wol_upload_guard_commit(&s,&k,0);
    assert(wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_write(&s,0x1008,8,9); /* adjacent non-alias */
    assert(wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_write(&s,0x1007,8,9); /* one-byte overlap */
    assert(!wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_commit(&s,&k,1); /* GL error */
    assert(!wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_commit(&s,&k,0);
    assert(wol_upload_guard_prepare(&s,&k,p));
    p[7]=1;assert(!wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_commit(&s,&k,0);
    assert(wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_write(&s,0x9000,8,3); /* same GL name, other descriptor */
    assert(!wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_commit(&s,&k,0);
    k.context++;assert(!wol_upload_guard_prepare(&s,&k,p));
    wol_upload_guard_commit(&s,&k,0);
    k.id++;assert(!wol_upload_guard_prepare(&s,&k,p));
    k.bytes=0;assert(!wol_upload_guard_prepare(&s,&k,p));
    free(s.copy.snapshot);
}
'''
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);(d/'test.c').write_text(code)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(d/'test.c'),'-o',str(d/'test')],check=True)
            subprocess.run([str(d/'test')],check=True)
if __name__=='__main__':unittest.main()
