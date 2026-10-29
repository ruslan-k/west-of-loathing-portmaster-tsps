#!/usr/bin/env python3
"""Execute the update-v327680 UpRender component-settings hook outside the device.

The published header must (a) stay inert unless an env switch is set, (b) replay the
exact intercepted instruction, (c) rewrite only an exact 1920x1080 component size and
(d) fail closed when the intercepted instruction is not the pinned one.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_wol_memory_handheld import added_header

STUB = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
/* sys/wait.h would pull the real ucontext_t into this mock harness. */
extern pid_t waitpid(pid_t,int*,int);
#define LC2_MAIN_BASE 0x8005000ULL
#define PROT_READ 1
#define PROT_EXEC 4
#define PROT_WRITE 2
static uint8_t object[256];
static int stopped;
static char stop_name[64];
static void stop(const char *s,uint64_t p,uint64_t x,unsigned c){(void)p;(void)x;(void)c;
 snprintf(stop_name,sizeof stop_name,"%s",s);stopped=1;exit(42);}
static int accessible(uint64_t p,size_t n,int f){if(f==PROT_EXEC)return 1;(void)f;
 uint64_t base=(uintptr_t)object;
 return p>=base && p-base<=sizeof(object) && n<=sizeof(object)-(p-base);}
static ssize_t mock_pread(int fd,void *out,size_t n,off_t p){(void)fd;
 uint64_t base=(uintptr_t)object,addr=(uint64_t)p;
 if(addr<base || addr-base>sizeof(object) || n>sizeof(object)-(addr-base))return -1;
 memcpy(out,(void *)(uintptr_t)addr,n);return (ssize_t)n;}
#define pread mock_pread
typedef struct {struct {uint64_t regs[31],sp,pc;} uc_mcontext;} ucontext_t;
'''


def harness(body: str) -> str:
    return STUB + added_header('wol_uprender_v24.h') + body


MAIN = r'''
static void dims(uint32_t w,uint32_t h){memcpy(object+32,&w,4);memcpy(object+36,&h,4);}
static uint64_t pc0(void){return LC2_MAIN_BASE+wol_up24_sites[0].offset;}
static uint32_t op0(void){return wol_up24_sites[0].opcode;}
static uint64_t pc1(void){return LC2_MAIN_BASE+wol_up24_sites[1].offset;}
static uint32_t op1(void){return wol_up24_sites[1].opcode;}
static uint64_t site_pc(unsigned i){return LC2_MAIN_BASE+wol_up24_sites[i].offset;}
static uint32_t site_op(unsigned i){return wol_up24_sites[i].opcode;}
int main(void){
 dims(1920,1080);
 {  /* default off: no site, no register change */
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc0();
  if(wol_up24_site(pc0(),op0()))return 1;
  if(wol_up24_handle(pc0(),op0(),&c))return 2;
  if(c.uc_mcontext.pc!=pc0())return 3;
 }
 {  /* trace only: instruction is replayed, dimensions stay as loaded */
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc0();wol_up24_mem=1;wol_up24_trace=1;wol_up24_patch=0;
  if(!wol_up24_site(pc0(),op0()))return 4;
  if(!wol_up24_handle(pc0(),op0(),&c))return 5;
  if(c.uc_mcontext.pc!=pc0()+4)return 6;
  if(c.uc_mcontext.regs[8]!=1920||c.uc_mcontext.regs[9]!=1080)return 7;
  if(memcmp(object+32,&(uint32_t[2]){1920,1080},8))return 8; /* never written */
  wol_up24_trace=0;wol_up24_patch=1;
 }
 {  /* exact 1920x1080 -> 1280x720 */
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc0();
  if(!wol_up24_handle(pc0(),op0(),&c))return 9;
  if(c.uc_mcontext.regs[8]!=1280||c.uc_mcontext.regs[9]!=720)return 10;
 }
 {  /* second visit of the same component is stable */
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc0();
  if(!wol_up24_handle(pc0(),op0(),&c))return 11;
  if(c.uc_mcontext.regs[8]!=1280||c.uc_mcontext.regs[9]!=720)return 12;
 }
 {  /* every other aspect/size is passed through untouched */
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc0();
  uint32_t keep[3][2]={{1920,720},{1024,768},{3840,2160}};
  for(unsigned i=0;i<3;i++){
   dims(keep[i][0],keep[i][1]);
   if(!wol_up24_handle(pc0(),op0(),&c))return 13;
   if(c.uc_mcontext.regs[8]!=keep[i][0]||c.uc_mcontext.regs[9]!=keep[i][1])return 14;
  }
 }
 {  /* a different instruction address never registers the site */
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;
  if(wol_up24_site(pc0()+4,op0()))return 15;
  if(wol_up24_handle(pc0()+4,op0(),&c))return 16;
 }
 dims(1920,1080);
 {  /* Screen width/height results: only the exact 1920/1080 is rewritten */
  uint32_t w0=1920,h0=1080,other=1600;
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;
  c.uc_mcontext.regs[0]=w0;c.uc_mcontext.pc=site_pc(2);
  if(!wol_up24_handle(site_pc(2),site_op(2),&c))return 30;
  uint32_t got=0;memcpy(&got,object+0x60,4);if(got!=1280||c.uc_mcontext.regs[0]!=1280)return 31;
  c.uc_mcontext.regs[0]=h0;c.uc_mcontext.pc=site_pc(3);
  if(!wol_up24_handle(site_pc(3),site_op(3),&c))return 32;
  memcpy(&got,object+0x64,4);if(got!=720||c.uc_mcontext.regs[0]!=720)return 33;
  c.uc_mcontext.regs[0]=other;c.uc_mcontext.pc=site_pc(2);
  if(!wol_up24_handle(site_pc(2),site_op(2),&c))return 34;
  memcpy(&got,object+0x60,4);if(got!=other)return 35;
 }
 {  /* build site is observation-only: never registered while the rewrite is on */
  if(wol_up24_site(pc1(),op1()))return 22;
  if(wol_up24_handle(pc1(),op1(),0))return 23;
  wol_up24_patch=0;wol_up24_trace=1;
  if(!wol_up24_site(pc1(),op1()))return 24;
  uint32_t cw=1920,ch=1080;memcpy(object+0x68,&cw,4);memcpy(object+0x6c,&ch,4);
  ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc1();
  if(!wol_up24_handle(pc1(),op1(),&c))return 25;
  int32_t imm=(int32_t)(op1()&0x03ffffffU);if(imm&0x02000000)imm-=0x04000000;
  if(c.uc_mcontext.pc!=pc1()+(int64_t)imm*4)return 26;
  if(c.uc_mcontext.regs[30]!=pc1()+4)return 27;
  if(!wol_up24_trace || wol_up24_patch)return 28;
  wol_up24_trace=0;wol_up24_patch=1;
 }
 {  /* wrong opcode at the pinned address fails closed in a child */
  pid_t p=fork();
  if(!p) {
   ucontext_t c={0};c.uc_mcontext.regs[19]=(uintptr_t)object;c.uc_mcontext.pc=pc0();
   wol_up24_site(pc0(),0xdeadbeefU);
   _exit((int)c.uc_mcontext.pc);
  }
  int st=0;if(waitpid(p,&st,0)!=p)return 17;
  if(WIFEXITED(st) && WEXITSTATUS(st)==0)return 18;
  if(!WIFEXITED(st) || WEXITSTATUS(st)!=42)return 19;
 }
 {  /* unreadable owner fails closed instead of returning stale registers */
  pid_t p=fork();
  if(!p) {
   ucontext_t c={0};c.uc_mcontext.regs[19]=0x10;c.uc_mcontext.pc=pc0();
   wol_up24_handle(pc0(),op0(),&c);
   _exit((int)c.uc_mcontext.regs[8]);
  }
  int st=0;if(waitpid(p,&st,0)!=p)return 20;
  if(WIFEXITED(st) && WEXITSTATUS(st)==0)return 21;
 }
 return 0;
}
'''


class UpRenderV24(unittest.TestCase):
    def test_published_hook_replays_and_rewrites_only_1920x1080(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 't.c'
            p.write_text(harness(MAIN))
            subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror', str(p), '-o', str(Path(d) / 't')], check=True)
            subprocess.run([str(Path(d) / 't')], check=True)


if __name__ == '__main__':
    unittest.main()
