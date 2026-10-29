"""Offline GetPseudoDeviceId: stable app-scoped profile ID, strict IPC shape."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def added_sources():
    patch=(ROOT/'runtime/wol-adapter.patch').read_text()
    return '\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))

class DeviceIdTests(unittest.TestCase):
    def fixture(self,directory):
        source=added_sources()
        begin='/* WOL_PSEUDO_DEVICE_ID_BEGIN */';end='/* WOL_PSEUDO_DEVICE_ID_END */'
        self.assertTrue(begin in source,'missing persistent offline device identity implementation')
        helper=source.split(begin,1)[1].split(end,1)[0]
        begin='/* WOL_PSEUDO_DEVICE_REPLY_BEGIN */';end='/* WOL_PSEUDO_DEVICE_REPLY_END */'
        self.assertIn(begin,source,'missing ApplicationFunctions command50 reply')
        reply=source.split(begin,1)[1].split(end,1)[0]
        code=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>
'''+helper+r'''
#define LC2_PROGRAM_ID UINT64_C(0x010031b00a4e8000)
#define EP_APP_FUNCTIONS 14
static int laboratory_save_fd=-1;
static unsigned calls,replies;
static uint8_t reply_bytes[16];
static void save_open(uint64_t pc){(void)pc;calls++;assert(laboratory_save_fd>=0);}
static void stop(const char *status,uint64_t pc,uint64_t detail,int code){(void)pc;(void)detail;puts(status);exit(code);}
static void ipc_reply(uint8_t *b,unsigned token,unsigned result,const void *out,size_t size,unsigned n,unsigned domain){
    (void)b;(void)token;(void)n;(void)domain;assert(result==0&&size==16);memcpy(reply_bytes,out,16);replies++;
}
struct request {unsigned command,send_pid,copies,num_inputs,num_outputs,input_objects,token,domain;size_t data_size;};
static int dispatch(struct request *req,unsigned endpoint){uint8_t *buffer=NULL;uint64_t pc=0;
'''+reply+r'''
return 0;
}
int main(int argc,char **argv){
    assert(argc==4);laboratory_save_fd=open(argv[1],O_RDONLY|O_DIRECTORY);assert(laboratory_save_fd>=0);
    uint64_t program=strtoull(argv[2],NULL,0);uint8_t out[16];memset(out,0xa5,sizeof out);
    if(strcmp(argv[3],"helper")){
        struct request r={.command=50,.token=7,.domain=1};
        if(!strcmp(argv[3],"payload"))r.data_size=1;
        if(!strcmp(argv[3],"pid"))r.send_pid=1;
        if(!strcmp(argv[3],"copies"))r.copies=1;
        if(!strcmp(argv[3],"input"))r.num_inputs=1;
        if(!strcmp(argv[3],"output"))r.num_outputs=1;
        if(!strcmp(argv[3],"objects"))r.input_objects=1;
        if(!strcmp(argv[3],"other")){r.command=51;assert(!dispatch(&r,EP_APP_FUNCTIONS));assert(!calls&&!replies);return 0;}
        assert(dispatch(&r,EP_APP_FUNCTIONS));assert(calls==1&&replies==1);memcpy(out,reply_bytes,16);
    } else if(wol_profile_device_id(laboratory_save_fd,program,out)){
        for(unsigned i=0;i<16;i++)assert(out[i]==0xa5);
        printf("IO_ERROR %d\n",errno);return 3;
    }
    for(unsigned i=0;i<16;i++){printf("%02x",out[i]);}putchar('\n');return 0;
}
'''
        c=Path(directory)/'id.c';binary=Path(directory)/'id';c.write_text(code)
        p=subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return binary

    def test_persistent_identity_is_app_scoped_and_reply_has_exact_uuid_size(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);binary=self.fixture(root);profile=root/'profile';profile.mkdir()
            def run(program,mode='helper'):
                return subprocess.run([str(binary),str(profile),program,mode],capture_output=True,text=True,timeout=3)
            one=run('0x010031b00a4e8000');self.assertEqual(one.returncode,0,one.stdout+one.stderr)
            two=run('0x010031b00a4e8000');self.assertEqual(one.stdout,two.stdout)
            self.assertEqual(len(bytes.fromhex(one.stdout.strip())),16)
            other=run('0x010031b00a4e9000');self.assertEqual(other.returncode,0,other.stdout+other.stderr);self.assertNotEqual(one.stdout,other.stdout)
            response=run('0','request');self.assertEqual(response.returncode,0,response.stdout+response.stderr);self.assertEqual(response.stdout,one.stdout)
            for mode in ('payload','pid','copies','input','output','objects'):
                p=run('0',mode);self.assertEqual(p.returncode,24,p.stdout+p.stderr);self.assertIn('INVALID_PSEUDO_DEVICE_ID_REQUEST',p.stdout)
            self.assertEqual(run('0','other').returncode,0)

    def test_corrupt_or_symlinked_identity_is_refused_without_overwriting(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);binary=self.fixture(root);profile=root/'profile';profile.mkdir()
            def run():return subprocess.run([str(binary),str(profile),'0x010031b00a4e8000','helper'],capture_output=True,text=True,timeout=3)
            self.assertEqual(run().returncode,0)
            files=list(profile.iterdir());self.assertEqual(len(files),1);identity=files[0]
            identity.write_bytes(b'broken');p=run();self.assertEqual(p.returncode,3,p.stdout+p.stderr);self.assertEqual(identity.read_bytes(),b'broken')
            identity.unlink();target=root/'sentinel';target.write_bytes(bytes(range(16)));identity.symlink_to(target)
            p=run();self.assertEqual(p.returncode,3,p.stdout+p.stderr);self.assertEqual(target.read_bytes(),bytes(range(16)))
            identity.unlink();import os;os.mkfifo(identity)
            p=run();self.assertEqual(p.returncode,3,p.stdout+p.stderr)

if __name__=='__main__':unittest.main()
