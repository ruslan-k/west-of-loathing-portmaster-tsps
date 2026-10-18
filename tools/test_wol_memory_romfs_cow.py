#!/usr/bin/env python3
"""Compile/run actual disk-backed RomFS read helper against anonymous output pages."""
import os,subprocess,tempfile,unittest
from pathlib import Path
from test_wol_memory_handheld import added_header

class RomfsCowContract(unittest.TestCase):
    def test_gate_refuses_aliases_attributes_and_conflicting_policies(self):
        gate=added_header('wol_romfs_gate.h')
        code=r'''
#define _GNU_SOURCE
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define HEAP_BASE 0x10000000ULL
static uint64_t heap_size=0x100000;
struct region {uint64_t base,size;unsigned perm,state,attr;const char *name;};
static struct region region={HEAP_BASE,0x100000,3,5,0,"main_heap"};
static struct region query(uint64_t a){(void)a;return region;}
static unsigned guard;
static unsigned normal_guard_overlap(uint64_t a,uint64_t n){(void)a;(void)n;return guard;}
static unsigned naliases;
static struct {uint64_t source,dest,size;} aliases[2];
static struct {uint64_t address,size;unsigned open;} transfer_regions[16];
'''+gate+r'''
int main(void) {
    uint64_t a=HEAP_BASE+4096,n=8192;
    unsetenv("T2_GUEST_ZRAM");unsetenv("MEGAMAN_LAZY_ZERO");unsetenv("T2_PAGE_CATALOGUE");
    assert(wol_romfs_output_eligible(a,n));
    assert(!wol_romfs_output_eligible(a,0));assert(!wol_romfs_output_eligible(a,UINT64_MAX));
    region.attr=1;assert(!wol_romfs_output_eligible(a,n));region.attr=0;
    region.perm=1;assert(!wol_romfs_output_eligible(a,n));region.perm=3;
    region.name="alias_physical";assert(!wol_romfs_output_eligible(a,n));region.name="main_heap";
    guard=1;assert(!wol_romfs_output_eligible(a,n));guard=0;
    naliases=1;aliases[0].source=a+n-1;aliases[0].size=4096;
    assert(!wol_romfs_output_eligible(a,n));aliases[0].source=a+n;
    assert(wol_romfs_output_eligible(a,n));naliases=0;
    transfer_regions[0].address=a;transfer_regions[0].size=n;transfer_regions[0].open=1;
    assert(!wol_romfs_output_eligible(a,n));transfer_regions[0].open=0;
    setenv("T2_GUEST_ZRAM","1",1);assert(!wol_romfs_output_eligible(a,n));setenv("T2_GUEST_ZRAM","0",1);
    setenv("MEGAMAN_LAZY_ZERO","1",1);assert(!wol_romfs_output_eligible(a,n));setenv("MEGAMAN_LAZY_ZERO","0",1);
    setenv("T2_PAGE_CATALOGUE","x",1);assert(!wol_romfs_output_eligible(a,n));unsetenv("T2_PAGE_CATALOGUE");
    assert(wol_romfs_output_eligible(a,n));
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'gate.c').write_text(code)
            subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'gate.c'),'-o',str(p/'gate')],check=True)
            subprocess.run([str(p/'gate')],check=True)

    def test_exact_unaligned_read_edges_private_writes_and_fail_closed(self):
        header=added_header('wol_romfs_cow.h')
        code=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>
'''+header+r'''
int main(int argc,char **argv) {
    assert(argc==2);
    char input[512];assert(snprintf(input,sizeof input,"%s/input",argv[1])>0);
    int fd=open(input,O_CREAT|O_EXCL|O_RDWR,0600);assert(fd>=0);
    enum {N=45056};uint8_t original[N];
    for(unsigned i=0;i<N;i++)original[i]=(uint8_t)(i*71+(i>>7));
    assert(write(fd,original,N)==N);
    for(unsigned delta=0;delta<4096;delta+=113) {
        uint8_t *base=mmap(NULL,N,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(base!=MAP_FAILED);
        memset(base,0xa5,N);size_t size=19000;unsigned off=208;
        struct wol_romfs_cow_result r={0};
        assert(wol_romfs_cow_read(fd,off,base+delta,size,argv[1],&r)==1);
        assert(r.mapped>=12288 && !(r.address%4096) && !(r.mapped%4096));
        assert(!memcmp(base+delta,original+off,size));
        /* Inspect the actual VMA: an anonymous fallback or shared file mapping
         * must fail the test even if its bytes happen to be correct. */
        FILE *maps=fopen("/proc/self/maps","r");assert(maps);char line[1024];unsigned found=0;
        while(fgets(line,sizeof line,maps)) {
            unsigned long long lo=0,hi=0;char perms[8]={0};
            if(sscanf(line,"%llx-%llx %7s",&lo,&hi,perms)==3 && lo==r.address && hi==r.address+r.mapped) {
                assert(!strcmp(perms,"rw-p") && strstr(line,"wol-romfs-cow-") && strstr(line,"(deleted)"));found++;
            }
        }
        fclose(maps);assert(found==1);
        for(unsigned i=0;i<delta;i++)assert(base[i]==0xa5);
        for(unsigned i=delta+size;i<N;i++)assert(base[i]==0xa5);
        uint8_t *a=(void *)(uintptr_t)r.address;uint8_t old=a[19];a[19]^=0xff;
        uint8_t disk=0;assert(pread(fd,&disk,1,off+(r.address-(uintptr_t)(base+delta))+19)==1);assert(disk==old);
        /* Same output may be reused/overwritten by later ordinary reads. */
        assert(pread(fd,base+delta,500,317)==500);assert(!memcmp(base+delta,original+317,500));
        assert(munmap(base,N)==0);
    }
    uint8_t *b=mmap(NULL,N,3,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(b!=MAP_FAILED);memset(b,0x6b,N);
    struct wol_romfs_cow_result r={0};
    assert(!wol_romfs_cow_read(-1,0,b+32,20000,argv[1],&r));
    assert(!wol_romfs_cow_read(fd,0,b+32,20000,"/nonexistent/wol-dir",&r));
    assert(!wol_romfs_cow_read(fd,N-1,b+32,20000,argv[1],&r));
    assert(!wol_romfs_cow_read(fd,UINT64_MAX,b+32,20000,argv[1],&r));
    assert(!wol_romfs_cow_read(fd,0,b+32,0,argv[1],&r));
    for(unsigned i=0;i<N;i++)assert(b[i]==0x6b);
    assert(!munmap(b,N));close(fd);unlink(input);puts("ROMFS_COW_OK");
}
'''
        if os.environ.get('WOL_COW_FIXTURE_OUT'):
            Path(os.environ['WOL_COW_FIXTURE_OUT']).write_text(code)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'test.c').write_text(code)
            subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
            r=subprocess.run([str(p/'test'),str(p)],check=True,capture_output=True,text=True)
            self.assertIn('ROMFS_COW_OK',r.stdout)
            self.assertEqual(set(x.name for x in p.iterdir()),{'test.c','test'})

if __name__=='__main__':unittest.main()
