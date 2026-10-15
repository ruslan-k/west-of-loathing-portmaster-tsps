#!/usr/bin/env python3
"""Exhaust native 4444 values/swizzles; execute exact opt-in eligibility code."""
from pathlib import Path
import os,subprocess,sys,tempfile
n=Path(sys.argv[1]);h=(n/'nvn_cpu_packed.h').read_text()
assert '/* WOL_PACKED4444_BEGIN */' in h,'missing isolated WoL opt-in eligibility gate'
helper=h.split('/* WOL_PACKED4444_BEGIN */',1)[1].split('/* WOL_PACKED4444_END */',1)[0]
pre=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include "nvn_texture_formats.h"
struct nvn_pool {unsigned flags;};static struct nvn_pool pool={.flags=0x22};
struct nvn_texture {uint64_t id;struct nvn_pool *pool; struct {unsigned format,target,depth,levels,samples,width,height,flags,packaged,packaged_layout,gl_name;uint32_t swizzle[4];} b;unsigned host_half,host_scaled,packaged_lazy,composition_target_seen;};
static uint64_t nvn_caller;
static void stop(const char *s,uint64_t a,uint64_t b,int c){(void)s;(void)a;(void)b;exit(c);}
'''
main=r'''
int main(int argc,char **argv){(void)argv;
 assert(nvn_texture_upload_bytes(0x8033)==2);
 assert(nvn_texture_format_bytes(0x39)==2);
 unsigned cases=0;
 if(argc==1)for(unsigned selectors=0;selectors<1296;selectors++){
  unsigned z=selectors;uint32_t sw[4];for(unsigned c=0;c<4;c++){sw[c]=z%6;z/=6;}
  assert(nvn_texture_swizzle_supported(0x39,sw));
  for(unsigned word=0;word<65536;word++){
   uint8_t src[2]={(uint8_t)word,(uint8_t)(word>>8)},rgba[4],packed[2];uint16_t v;
   assert(nvn_texture_decode_rgba(0x39,sw,rgba,src,1));
   assert(nvn_texture_decode_upload(0x39,sw,0x8033,packed,src,1));memcpy(&v,packed,2);
   for(unsigned c=0;c<4;c++)assert(rgba[c]==((v>>(12-4*c))&15)*17);
   cases++;
  }
 }
 uint32_t bad[4]={2,3,4,6};uint8_t src[2]={0},dst[4];
 assert(!nvn_texture_decode_upload(0x39,bad,0x8033,dst,src,1));
 uint32_t identity[4]={2,3,4,5},bgra[4]={4,3,2,5};
 assert(nvn_texture_decode_upload(0x97,identity,0x8034,dst,src,1));
 assert(!nvn_texture_decode_upload(0x97,bgra,0x8034,dst,src,1));
 printf("PASS exhaustive 4444: %u pixels across all 1296 legal swizzles; invalid swizzles rejected; 5551 contract unchanged\n",cases);
 struct nvn_texture t={.id=1,.pool=&pool,.b={.format=0x39,.target=1,.depth=1,.levels=1,.width=2048,.height=2048,.swizzle={4,3,2,5}}};
 unsigned wanted=getenv("EXPECT_PACKED")?0x8033U:0U;
 assert(wol_packed4444_candidate(&t)==wanted);setenv("WOL_PACKED4444",wanted?"0":"1",1);
 /* Configuration is immutable: a new process is required to opt in. */
 assert(wol_packed4444_candidate(&t)==wanted);
 assert(wol_packed4444_eligible(&t));
 #define REFUSE(field,value) {unsigned old=t.field;t.field=value;assert(!wol_packed4444_eligible(&t));t.field=old;}
 REFUSE(b.format,0x44);REFUSE(b.flags,8);REFUSE(b.target,8);REFUSE(b.depth,2);REFUSE(b.levels,0);REFUSE(b.levels,15);REFUSE(b.samples,2);
 REFUSE(b.width,0);REFUSE(b.height,4097);REFUSE(b.packaged,1);REFUSE(b.packaged_layout,1);REFUSE(b.gl_name,2);
 REFUSE(host_scaled,1);REFUSE(host_half,1);REFUSE(packaged_lazy,1);REFUSE(composition_target_seen,1);REFUSE(b.swizzle[0],6);
 pool.flags=0x14;assert(!wol_packed4444_eligible(&t));pool.flags=0x22;
 t.b.levels=12;assert(wol_packed4444_eligible(&t));
 printf("PASS eligibility, immutable/default-off opt-in, checked %u pixels\n",cases);return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='wol-packed4444-',dir=os.environ.get('TMPDIR')) as d:
 p=Path(d)
 (p/'test.c').write_text(pre+helper+main)
 subprocess.run(['cc','-O2','-D_POSIX_C_SOURCE=200809L','-std=c11','-Wall','-Wextra','-Werror','-I',str(n),str(p/'test.c'),'-pthread','-o',str(p/'test')],check=True)
 for value,rc in [(None,0),('0',0),('1',0),('01',24),('true',24)]:
  env=dict(os.environ);env.pop('WOL_PACKED4444',None);env.pop('EXPECT_PACKED',None)
  if value is not None:env['WOL_PACKED4444']=value
  if value=='1':env['EXPECT_PACKED']='1'
  args=[str(p/'test')]+([] if value is None else ['--eligibility-only'])
  result=subprocess.run(args,env=env);assert result.returncode==rc,(value,result.returncode,rc)
  print('PASS packed option',value,'rc',rc)
