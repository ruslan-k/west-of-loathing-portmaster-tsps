import subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# The in-repo copy is authoritative for CI until the overlay can be rebuilt against the exact
# game image (roadmap 26.3a); a missing header must fail, never skip.
HEADER=ROOT/'evidence'/'horizon-hd1-2026-10-30'/'wol_da_split.h'


class DrawArraysLedger(unittest.TestCase):
    def test_last_stage_does_not_alias_the_enclosing_draw(self):
        self.assertTrue(HEADER.is_file(),f'ledger header missing: {HEADER}')
        h=HEADER.read_text()
        c=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
'''+h+r'''
int main(void) {
 struct wol_da_state s;memset(&s,0,sizeof s);

 /* default OFF: nothing is recorded even if spans and a draw are opened */
 wol_da_open_draw(&s);wol_da_fake_clock=100;wol_da_mark(&s,0);wol_da_fake_clock=160;
 wol_da_close(&s,0);wol_da_fake_clock=200;wol_da_close_draw(&s);
 assert(s.total_cpu==0 && s.cpu[0]==0 && s.draws==0);

 s.on=1;
 /* frame 1: stages 0 and 10 (NPS_SUBMIT is the last NPS_* id) inside one draw.
    Draw spans 1000..1300, stages explain 60+40, residual must be 200. */
 wol_da_fake_clock=1000;wol_da_open_draw(&s);
 wol_da_fake_clock=1000;wol_da_mark(&s,0);wol_da_fake_clock=1060;wol_da_close(&s,0);
 wol_da_fake_clock=1200;wol_da_mark(&s,10);wol_da_fake_clock=1240;wol_da_close(&s,10);
 wol_da_fake_clock=1300;wol_da_close_draw(&s);
 assert(s.cpu[0]==60 && s.cpu[10]==40);
 assert(s.calls[10]==1);
 assert(s.total_cpu==300 && s.total_wall==300);   /* measured from draw entry, not from submit */
 assert(wol_da_residual_cpu(&s)==200);            /* submit belongs to the stage sum */

 /* frame 2 accumulates instead of restarting the enclosing clock */
 wol_da_fake_clock=2000;wol_da_open_draw(&s);
 wol_da_fake_clock=2000;wol_da_mark(&s,10);wol_da_fake_clock=2050;wol_da_close(&s,10);
 wol_da_fake_clock=2100;wol_da_close_draw(&s);
 assert(s.draws==2 && s.cpu[10]==90 && s.calls[10]==2);
 assert(s.total_cpu==400);
 assert(wol_da_residual_cpu(&s)==250);   /* 400 total - (60+40+50) staged */

 /* marks while closed are ignored */
 wol_da_fake_clock=3000;wol_da_mark(&s,3);wol_da_fake_clock=3100;wol_da_close(&s,3);
 assert(s.cpu[3]==0);

 wol_da_reset(&s);
 assert(s.total_cpu==0 && s.cpu[0]==0 && s.cpu[10]==0 && s.draws==0 && s.draw_wall_t0==0);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'t.c').write_text(c)
            subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-DWOL_DA_TEST_CLOCK',str(p/'t.c'),'-o',str(p/'t')],check=True)
            subprocess.run([str(p/'t')],check=True)


if __name__=='__main__':unittest.main()
