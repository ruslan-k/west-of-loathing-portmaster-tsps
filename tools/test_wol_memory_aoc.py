"""Pinned owned DLC: actual AOC replies, pagination and malformed-request refusal."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SECTION = 'ecab0ad27889a320ae6965413a06b1d99af4aef1cda65c7665ea6015788a13d0'


class AocTests(unittest.TestCase):
    def test_owned_house_replies_and_refusals(self):
        patch = (ROOT / 'runtime/wol-adapter.patch').read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        self.assertTrue('/* WOL_AOC_HOUSE_BEGIN */' in added,
                        'missing content-bound AOC implementation')
        body = added.split('/* WOL_AOC_HOUSE_BEGIN */', 1)[1].split('/* WOL_AOC_HOUSE_END */', 1)[0]
        code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define EP_AOC 18
#define LC2_PROGRAM_ID UINT64_C(0x010031b00a4e8000)
static const char *LC2_ROMFS_SHA256;
struct ipc_span {uint64_t address,size;};
struct request {
    unsigned command,send_pid,copies,num_inputs,num_outputs,input_objects,token,domain;
    size_t data_size;const uint8_t *data;struct ipc_span outputs[1];
};
static uint32_t read32(const void *p){uint32_t v;memcpy(&v,p,4);return v;}
static void put32(void *p,uint32_t v){memcpy(p,&v,4);}
static uint8_t response[16];static size_t response_size;
/* File availability is exercised by test_wol_memory_aoc_storage. */
static void wol_house_romfs_open(uint64_t pc){(void)pc;}
static void stop(const char *status,uint64_t pc,uint64_t detail,int code){
    (void)pc;(void)detail;puts(status);exit(code);
}
static void ipc_reply(uint8_t *p,unsigned token,uint32_t result,const void *data,size_t size,unsigned moved,unsigned domain){
    (void)p;assert(token==7&&result==0&&moved==0&&domain==1&&size<=sizeof(response));
    response_size=size;if(size)memcpy(response,data,size);
}
static void dispatch(struct request req){unsigned endpoint=EP_AOC;uint64_t pc=0,handle=0;uint8_t *buffer=NULL;
''' + body + r'''
    uint32_t count=0;ipc_reply(buffer,req.token,0,&count,4,0,req.domain);
}
int main(int argc,char **argv){
    assert(argc==3);LC2_ROMFS_SHA256=argv[1];const char *mode=argv[2];
    uint8_t data[40]={0},output[12];memset(output,0xa5,sizeof(output));
    struct request r={.command=2,.send_pid=1,.data_size=12,.data=data,.token=7,.domain=1};
    if(!strncmp(mode,"list",4)){
        r.command=3;r.data_size=32;put32(data,0);put32(data+4,2);
        r.num_outputs=1;r.outputs[0]=(struct ipc_span){(uintptr_t)output,8};
        if(!strcmp(mode,"list-end"))put32(data,1);
        if(!strcmp(mode,"list-negative"))put32(data,UINT32_MAX);
        if(!strcmp(mode,"list-short"))r.outputs[0].size=4;
        if(!strcmp(mode,"list-missing"))r.num_outputs=0;
        if(!strcmp(mode,"list-zero")){put32(data+4,0);r.num_outputs=0;}
    }
    if(!strcmp(mode,"base"))r.command=5;
    if(!strncmp(mode,"prepare",7)){r.command=7;r.data_size=20;put32(data,1);if(!strcmp(mode,"prepare-other"))put32(data,2);}
    if(!strcmp(mode,"pid"))r.send_pid=0;
    if(!strcmp(mode,"payload"))r.data_size=7;
    if(!strcmp(mode,"oversize"))r.data_size=28;
    if(!strcmp(mode,"copies"))r.copies=1;
    if(!strcmp(mode,"input"))r.num_inputs=1;
    if(!strcmp(mode,"objects"))r.input_objects=1;
    if(!strcmp(mode,"foreign-pid"))data[0]=1;
    dispatch(r);
    if(!strcmp(mode,"base")){uint64_t v;assert(response_size==8);memcpy(&v,response,8);assert(v==UINT64_C(0x010031b00a4e9000));}
    else if(!strncmp(mode,"prepare",7))assert(response_size==0);
    else{
        assert(response_size==4);unsigned expected=strcmp(LC2_ROMFS_SHA256,"SECTION_HASH")==0;
        if(!strcmp(mode,"list-end")||!strcmp(mode,"list-zero"))expected=0;
        assert(read32(response)==expected);
    }
    if(!strcmp(mode,"list")){assert(read32(output)==1);for(unsigned i=4;i<sizeof(output);i++)assert(output[i]==0xa5);}
    else for(unsigned i=0;i<sizeof(output);i++)assert(output[i]==0xa5);
    return 0;
}
'''
        code = code.replace('SECTION_HASH', SECTION)
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'aoc.c'; binary = Path(td) / 'aoc'
            source.write_text(code)
            build = subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            for mode in ('count', 'list', 'list-end', 'list-zero', 'base', 'prepare'):
                with self.subTest(mode=mode):
                    p = subprocess.run([str(binary), SECTION, mode], capture_output=True, text=True)
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = subprocess.run([str(binary), 'unrecognized-base-image', 'count'], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            for mode in ('pid', 'payload', 'oversize', 'copies', 'input', 'objects', 'foreign-pid', 'list-negative', 'list-short', 'list-missing', 'prepare-other'):
                with self.subTest(refusal=mode):
                    p = subprocess.run([str(binary), SECTION, mode], capture_output=True, text=True)
                    self.assertEqual(p.returncode, 24, p.stdout + p.stderr)
                    self.assertIn('INVALID_AOC_', p.stdout)


if __name__ == '__main__':
    unittest.main()
