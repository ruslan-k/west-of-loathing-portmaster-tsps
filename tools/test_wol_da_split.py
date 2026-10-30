import subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HEADER=ROOT.parent/'..'/'spikes'/'wol-switch'/'wol-horizon-source'/'native'/'wol_da_split.h'


def _header():
    """The ledger header lives in the build source; fall back to the spike tree."""
    candidates=[HEADER,
        Path('/mnt/external/Hermes/spikes/wol-switch/wol-horizon-build-up24s2/source/native/wol_da_split.h'),
        Path('/mnt/external/Hermes/spikes/wol-switch/wol-horizon-source/native/wol_da_split.h')]
    for c in candidates:
        if c.is_file(): return c.read_text()
    raise unittest.SkipTest('wol_da_split.h not present in a build source tree')


class DrawArraysLedger(unittest.TestCase):
    def test_accumulates_non_overlapping_spans_and_residual(self):
        h=_header()
        c=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
'''+h+r'''
int main(void) {
 struct wol_da_state s;memset(&s,0,sizeof s);

 /* default OFF: an open/close pair must not record anything */
 wol_da_open_draw(&s);wol_da_fake_clock=100;wol_da_mark(&s,0);wol_da_fake_clock=160;
 wol_da_close(&s,0);wol_da_fake_clock=200;wol_da_close_draw(&s);
 assert(s.total_cpu==0 && s.cpu[0]==0 && s.draws==0);

 s.on=1;
 /* one draw: span0 60ns cpu, span1 40ns, draw total 150ns -> residual 50ns */
 wol_da_fake_clock=1000;wol_da_open_draw(&s);
 wol_da_fake_clock=1000;wol_da_mark(&s,0);wol_da_fake_clock=1060;wol_da_close(&s,0);
 wol_da_fake_clock=1060;wol_da_mark(&s,1);wol_da_fake_clock=1100;wol_da_close(&s,1);
 wol_da_fake_clock=1150;wol_da_close_draw(&s);
 assert(s.draws==1);
 assert(s.cpu[0]==60 && s.cpu[1]==40);
 assert(s.calls[0]==1 && s.calls[1]==1);
 assert(s.total_cpu==150 && s.total_wall==150);
 assert(wol_da_residual_cpu(&s)==50);

 /* closed state ignores stray marks */
 wol_da_fake_clock=2000;wol_da_mark(&s,2);wol_da_fake_clock=2100;wol_da_close(&s,2);
 assert(s.cpu[2]==0);

 /* reset clears every bucket */
 wol_da_reset(&s);
 assert(s.total_cpu==0 && s.cpu[0]==0 && s.cpu[1]==0 && s.draws==0);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'t.c').write_text(c)
            subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-DWOL_DA_TEST_CLOCK',str(p/'t.c'),'-o',str(p/'t')],check=True)
            subprocess.run([str(p/'t')],check=True)


if __name__=='__main__':unittest.main()
