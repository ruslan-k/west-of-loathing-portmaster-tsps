"""Owned DLC storage: exact root image, independent backing, strict FSP202 shape."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HouseStorageTests(unittest.TestCase):
    def test_dlc_uses_its_own_romfs_and_refuses_bad_requests_or_files(self):
        patch = (ROOT / 'runtime/wol-adapter.patch').read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertTrue('/* WOL_HOUSE_STORAGE_OPEN_BEGIN */' in added, 'missing separate DLC storage')
        # Preserve unchanged context too: the FSP block reuses an existing closing brace.
        patched = '\n'.join(line[1:] for line in patch.splitlines()
                            if line.startswith(('+', ' ')) and not line.startswith('+++'))
        def block(name):
            return patched.split('/* ' + name + '_BEGIN */', 1)[1].split('/* ' + name + '_END */', 1)[0]
        helper = block('WOL_HOUSE_STORAGE_OPEN')
        dispatch = block('WOL_HOUSE_STORAGE_FSP')
        selection = block('WOL_STORAGE_SOURCE')
        read = re.search(r'^\+\s+ssize_t got=(pread\(storage_fd,[^;]+\));', patch, re.M)
        self.assertIsNotNone(read, 'shared read must use the selected descriptor and prefix')
        assert read is not None
        self.assertIn('if(!house)romfs_overlay_apply(dest,offset,size);', added)
        self.assertIn('if(!house && wol_romfs_read_cow(storage_fd,storage_offset+offset,dest,size,pc))', added)
        code = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define LC2_PROGRAM_ID UINT64_C(0x010031b00a4e8000)
#define LC2_ROMFS_SHA256 "ecab0ad27889a320ae6965413a06b1d99af4aef1cda65c7665ea6015788a13d0"
#define ROMFS_OFFSET 64
#define EP_FSP 28
#define EP_STORAGE_ROMFS 29
#define EP_STORAGE_HOUSE 78
static int romfs_fd=-1;static uint64_t romfs_size=64;
struct request {unsigned command,send_pid,copies,input_objects,num_inputs,num_outputs;size_t data_size;const uint8_t *data;};
static unsigned child;
static void stop(const char *status,uint64_t pc,uint64_t detail,int code){(void)pc;(void)detail;puts(status);exit(code);}
static void ipc_child(void *buffer,void *s,struct request *req,unsigned endpoint,uint64_t pc){(void)buffer;(void)s;(void)req;(void)pc;child=endpoint;}
''' + helper + r'''
static int open_storage(struct request *req){unsigned endpoint=EP_FSP;uint64_t pc=0;void *buffer=NULL,*s=NULL;
''' + dispatch + r'''
return 0;}
static void read_storage(unsigned endpoint,uint64_t offset,uint64_t size,uint8_t *dest){
''' + selection.replace('return 0;', 'assert(0);') + r'''
    assert(storage_fd>=0);assert(offset<=storage_size&&size<=storage_size-offset);
    uint64_t done=0;assert(READ_CALL==(ssize_t)size);
}
int main(int argc,char **argv){
    assert(argc==2);const char *mode=argv[1];uint8_t data[32]={0};
    uint64_t id=UINT64_C(0x010031b00a4e9001);memcpy(data+8,&id,8);
    struct request r={.command=202,.data_size=16,.data=data};
    if(!strcmp(mode,"wrong-id")){id++;memcpy(data+8,&id,8);}
    if(!strcmp(mode,"pid"))r.send_pid=1;
    if(!strcmp(mode,"short"))r.data_size=15;
    if(!strcmp(mode,"oversize"))r.data_size=36;
    if(!strcmp(mode,"copies"))r.copies=1;
    if(!strcmp(mode,"objects"))r.input_objects=1;
    if(!strcmp(mode,"input"))r.num_inputs=1;
    if(!strcmp(mode,"output"))r.num_outputs=1;
    if(!strcmp(mode,"storage-id"))data[0]=255;
    assert(open_storage(&r)==1);assert(child==EP_STORAGE_HOUSE);
    int first=wol_house_romfs_fd;wol_house_romfs_open(0);assert(first==wol_house_romfs_fd);
    romfs_fd=open("program",O_RDONLY);assert(romfs_fd>=0);
    uint8_t got[16];read_storage(EP_STORAGE_HOUSE,0,16,got);
    for(unsigned i=0;i<16;i++)assert(got[i]==i);
    read_storage(EP_STORAGE_HOUSE,58907880-16,16,got);
    for(unsigned i=0;i<16;i++)assert(got[i]==0xd0+i);
    read_storage(EP_STORAGE_ROMFS,0,16,got);
    for(unsigned i=0;i<16;i++)assert(got[i]==0x80+i);
    close(romfs_fd);close(wol_house_romfs_fd);return 0;
}
'''.replace('READ_CALL', read.group(1))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'storage.c'; binary = root / 'storage'
            source.write_text(code)
            p = subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            house = root / 'wol-house.romfs'
            with house.open('wb') as f:
                f.write(bytes(range(16)));f.truncate(58907880);f.seek(58907880-16);f.write(bytes(range(0xd0,0xe0)))
            (root / 'program').write_bytes(bytes(64) + bytes(range(0x80,0x90)) + bytes(48))
            for mode in ('valid', 'wrong-id', 'pid', 'short', 'oversize', 'copies', 'objects', 'input', 'output', 'storage-id'):
                p = subprocess.run([str(binary), mode], cwd=root, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0 if mode == 'valid' else 24, p.stdout + p.stderr)
            house.unlink()
            for mode in ('missing-file', 'short-file', 'symlink', 'fifo'):
                if mode == 'short-file':house.write_bytes(b'short')
                if mode == 'symlink':house.symlink_to(root / 'program')
                if mode == 'fifo':os.mkfifo(house)
                p = subprocess.run([str(binary), 'valid'], cwd=root, capture_output=True, text=True, timeout=3)
                self.assertEqual(p.returncode, 21, mode + p.stdout + p.stderr)
                if house.exists() or house.is_symlink():house.unlink()
            self.assertEqual((root / 'program').read_bytes(), bytes(64) + bytes(range(0x80,0x90)) + bytes(48))


if __name__ == '__main__':
    unittest.main()
