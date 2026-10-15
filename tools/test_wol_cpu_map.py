#!/usr/bin/env python3
"""Host CPU placement must preserve the guest's logical 0..2 CPU ABI."""
from pathlib import Path
import os,subprocess,sys,tempfile
n=Path(sys.argv[1]);h=(n/'threading.h').read_text();loader=(n/'loader.c').read_text()
assert '/* WOL_CPU_MAP_BEGIN */' in h,'no host/logical CPU translation'
code=h.split('/* WOL_CPU_MAP_BEGIN */',1)[1].split('/* WOL_CPU_MAP_END */',1)[0]
assert 'CPU_SET(wol_host_cpu(i),&set)' in h
assert 'CPU_SET(wol_host_cpu(0),&affinity)' in loader
assert 'r[0]=wol_guest_cpu(sched_getcpu())' in loader
pre=r'''
#define _GNU_SOURCE
#define WOL_PLACEHOLDER_COMMANDS 1
#include <sched.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>

static void stop(const char *s,uint64_t a,uint64_t b,int c){(void)s;(void)a;(void)b;exit(c);}
static int host_cpus(pid_t p,size_t size,cpu_set_t *out){(void)p;(void)size;CPU_ZERO(out);for(unsigned i=0;i<(getenv("BLOCK_CPU6")?6:8);i++)CPU_SET(i,out);return 0;}
#define sched_getaffinity host_cpus
'''
main=r'''
int main(void){unsigned off=getenv("EXPECT_OFFSET")?4:0;
 for(unsigned i=0;i<3;i++){assert(wol_host_cpu(i)==i+off);assert(wol_guest_cpu(i+off)==i);}
 setenv("WOL_CPU_OFFSET",off?"0":"4",1);assert(wol_host_cpu(0)==off);
 if(off&&getenv("BAD_PHYSICAL")){wol_guest_cpu(0);return 1;}
 puts("PASS logical CPU ABI and immutable host mapping");return 0;}
'''
with tempfile.TemporaryDirectory(prefix='wol-cpu-map-',dir=os.environ.get('TMPDIR')) as d:
 p=Path(d);(p/'test.c').write_text(pre+code+main);subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-pthread','-o',str(p/'test')],check=True)
 for value,block,bad,rc in [(None,False,False,0),('0',False,False,0),('4',False,False,0),('3',False,False,24),('04',False,False,24),('4',True,False,24),('4',False,True,24)]:
  env=dict(os.environ)
  for k in ('WOL_CPU_OFFSET','EXPECT_OFFSET','BLOCK_CPU6','BAD_PHYSICAL'):env.pop(k,None)
  if value is not None:env['WOL_CPU_OFFSET']=value
  if value=='4':env['EXPECT_OFFSET']='1'
  if block:env['BLOCK_CPU6']='1'
  if bad:env['BAD_PHYSICAL']='1'
  r=subprocess.run([str(p/'test')],env=env,capture_output=True,text=True);assert r.returncode==rc,(value,block,bad,r.returncode,r.stdout,r.stderr)
  print('PASS offset',value,'blocked_cpu',block,'bad_physical',bad,'rc',rc)
