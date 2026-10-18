import subprocess,tempfile,unittest
from pathlib import Path
from test_wol_memory_handheld import added_header


class UpRenderPolicy(unittest.TestCase):
    def test_exact_owner_dimensions_atomic_default_off(self):
        h=added_header('wol_uprender_policy.h')
        c='#include <stdint.h>\n#include <assert.h>\n'+h+r'''
int main(void) {
 uint32_t dims[2]={1920,1080};
 assert(!wol_uprender_720(dims,0));assert(dims[0]==1920&&dims[1]==1080);
 assert(wol_uprender_720(dims,1));assert(dims[0]==1280&&dims[1]==720);
 assert(!wol_uprender_720(dims,1));assert(dims[0]==1280&&dims[1]==720);
 dims[0]=1920;dims[1]=720;assert(!wol_uprender_720(dims,1));assert(dims[0]==1920&&dims[1]==720);
 assert(!wol_uprender_720(0,1));
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'t.c').write_text(c)
            subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
            subprocess.run([str(p/'t')],check=True)


    def test_original_instruction_replay_and_component_only_write(self):
        h=added_header('wol_uprender_trace.h').replace('#include "wol_uprender_policy.h"',added_header('wol_uprender_policy.h'))
        c=r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
#include <sys/types.h>
#define LC2_MAIN_BASE 0x8005000ULL
#define PROT_READ 1
#define PROT_WRITE 2
#define PROT_EXEC 4
static uint64_t guest_thread_index;
typedef struct {struct {uint64_t regs[31],sp,pc;} uc_mcontext;} ucontext_t;
struct line {int unused;};
static void text(struct line*l,const char*s){(void)l;(void)s;}
static void hex(struct line*l,uint64_t x){(void)l;(void)x;}
static void location(struct line*l,uint64_t x){(void)l;(void)x;}
static void emit(struct line*l){(void)l;}
static void stop(const char*s,uint64_t p,uint64_t x,unsigned c){(void)s;(void)p;(void)x;(void)c;abort();}
static int accessible(uint64_t p,size_t n,int f){(void)p;(void)n;(void)f;return 1;}
static _Alignas(8) uint8_t object[88];
static ssize_t mock_pread(int fd,void*out,size_t n,off_t p){
 (void)fd;if((uint64_t)p!=(uintptr_t)object+32 || n!=8)return -1;
 memcpy(out,object+32,8);return 8;
}
#define pread mock_pread
'''+h+r'''
int main(void){
 uint8_t stack[256],before[88];memset(stack,0x5a,sizeof(stack));
 ucontext_t c={0};for(unsigned i=0;i<31;i++)c.uc_mcontext.regs[i]=i+100;
 c.uc_mcontext.sp=(uintptr_t)stack+256;wol_up_trace=1;wol_up_mem=1;
 uint64_t sp=c.uc_mcontext.sp;
 assert(wol_up_handle(LC2_MAIN_BASE+0x513df8,0xa9be4ff4U,&c));
 assert(c.uc_mcontext.sp==sp-32 && c.uc_mcontext.pc==LC2_MAIN_BASE+0x513dfc);
 uint64_t pair[2];memcpy(pair,stack+224,16);assert(pair[0]==120&&pair[1]==119);
 for(unsigned i=0;i<224;i++)assert(stack[i]==0x5a);
 assert(wol_up_handle(LC2_MAIN_BASE+0x513eb4,0xd10203ffU,&c));
 assert(c.uc_mcontext.sp==sp-160 && c.uc_mcontext.pc==LC2_MAIN_BASE+0x513eb8);
 assert(wol_up_handle(LC2_MAIN_BASE+0x514838,0x94074d1cU,&c));
 assert(c.uc_mcontext.regs[30]==LC2_MAIN_BASE+0x51483c && c.uc_mcontext.pc==LC2_MAIN_BASE+0x6e7ca8);
 assert(wol_up_handle(LC2_MAIN_BASE+0x51483c,0xf000cd08U,&c));
 assert(c.uc_mcontext.regs[8]==LC2_MAIN_BASE+0x1eb7000 && c.uc_mcontext.pc==LC2_MAIN_BASE+0x514840);
 c.uc_mcontext.regs[8]=LC2_MAIN_BASE+0xaf8120;
 assert(wol_up_handle(LC2_MAIN_BASE+0xc8b570,0xd63f0100U,&c));
 assert(c.uc_mcontext.regs[30]==LC2_MAIN_BASE+0xc8b574 && c.uc_mcontext.pc==LC2_MAIN_BASE+0xaf8120);
 uint32_t dims[2]={1920,1080};memset(object,0x5a,sizeof(object));memcpy(object+32,dims,8);memcpy(before,object,88);
 wol_up_patch=1;c.uc_mcontext.regs[0]=(uintptr_t)object;
 assert(wol_up_handle(LC2_MAIN_BASE+0x513df8,0xa9be4ff4U,&c));
 memcpy(dims,object+32,8);assert(dims[0]==1280&&dims[1]==720);
 assert(!memcmp(object,before,32)&&!memcmp(object+40,before+40,48));
 wol_up_patch=0;wol_up_trace=0;
 assert(!wol_up_handle(LC2_MAIN_BASE+0x513df8,0xa9be4ff4U,&c));
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'t.c').write_text(c)
            subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
            subprocess.run([str(p/'t')],check=True)


if __name__=='__main__':unittest.main()
