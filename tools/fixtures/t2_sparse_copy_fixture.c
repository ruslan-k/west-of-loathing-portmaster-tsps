/* TransferMemory sparse-copy contract fixture (roadmap §16.5).
 *
 * The scan block below is copied VERBATIM from the frozen build source
 * native/memory.h (file sha256 68974762e5551fbc57f6753e1c9c311488bcf2283642806e35051778be96ed8b,
 * span sha256 4f146003c1c920928f540a8dd067052a4f44ce69c2134b403b50ad34086c3041). Indentation is
 * preserved intentionally so the span stays byte-identical; the wrapper and matrix are fixture
 * scaffolding. Modes: `small` (1 MiB, host contract run) and `device` (64 MiB, adds Rss checks).
 * Prints `CASE <name> copied=<n> size=<n> ok=<0|1>` and, in device mode, `RSS <name> delta_kb=<n>`.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/mman.h>

#define PAGE 4096

static uint8_t *fresh(uint64_t bytes) {
    void *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(p==MAP_FAILED){perror("mmap");exit(2);}
    return p;
}
static long rss_kb(void) {
    FILE *f=fopen("/proc/self/smaps_rollup","r");
    if(!f)return -1;
    char line[256];long value=-1;
    while(fgets(line,sizeof line,f))if(!strncmp(line,"Rss:",4)){value=strtol(line+4,NULL,10);break;}
    fclose(f);return value;
}
static uint64_t rng_state=0x9e3779b97f4a7c15ULL;
static uint64_t next_u64(void){uint64_t x=rng_state;x^=x<<13;x^=x>>7;x^=x<<17;rng_state=x;return x;}
static uint64_t hash_bytes(const uint8_t *p,uint64_t n){uint64_t h=1469598103934665603ULL;for(uint64_t i=0;i<n;i++){h^=p[i];h*=1099511628211ULL;}return h;}

static int failures=0;
static void emit(const char *name,uint64_t copied,uint64_t size,int ok){
    printf("CASE %s copied=%llu size=%llu ok=%d\n",name,(unsigned long long)copied,(unsigned long long)size,ok);fflush(stdout);
    if(!ok)failures++;
}
static void emit_rss(const char *name,long delta_kb){
    printf("RSS %s delta_kb=%ld\n",name,delta_kb);fflush(stdout);
}

static uint64_t t2_fixture_sparse_scan(uint8_t *copy,uint64_t address,uint64_t size) {
    unsigned sparse=1;
uint64_t copied=size,skipped=0;
    if(sparse) {
        /* This destination is fresh anonymous zero-fill. Preserve every
         * nonzero page, leaving zero pages uncommitted. The caller hands off
         * the source exclusively, as required by the original memcpy path;
         * source protection, service ownership and full copyback stay intact. */
        static const uint8_t zero[PAGE];copied=0;
        for(uint64_t off=0;off<size;off+=PAGE) {
            const void *from=(const void *)(uintptr_t)(address+off);
            if(memcmp(from,zero,PAGE)){memcpy((uint8_t *)copy+off,from,PAGE);copied+=PAGE;}
            else skipped+=PAGE;
        }
    } else memcpy(copy,(void *)(uintptr_t)address,size);
    if(copied+skipped!=size){fprintf(stderr,"accounting mismatch\n");exit(3);}
    return copied;
}

static void pattern_nonzero(uint8_t *p,uint64_t pages,uint64_t stride){
    for(uint64_t i=0;i<pages;i+=stride) {
        uint64_t v=next_u64();
        memcpy(p+i*PAGE,&v,8);
        p[i*PAGE+8]=(uint8_t)(v>>32);
    }
}
static void pattern_dense(uint8_t *p,uint64_t size){
    for(uint64_t off=0;off<size;off+=8){uint64_t v=next_u64();memcpy(p+off,&v,8);}
}

int main(int argc,char **argv){
    int device=argc>1 && !strcmp(argv[1],"device");
    uint64_t size=device?(64ULL<<20):(1ULL<<20);
    uint64_t pages=size/PAGE;
    /* ---- all_zero: every page skipped, destination reads zero, byte-equal ---- */
    {
        uint8_t *src=fresh(size);uint8_t *dst=fresh(size);
        memset(src,0,size); /* resident zero source */
        long before=rss_kb();
        uint64_t copied=t2_fixture_sparse_scan(dst,(uint64_t)(uintptr_t)src,size);
        long after=rss_kb();
        int ok=(copied==0)&&(memcmp(dst,src,size)==0);
        emit("all_zero",copied,size,ok);
        if(device)emit_rss("all_zero",after-before);
        munmap(src,size);munmap(dst,size);
    }
    /* ---- sparse_mixed: only the patterned pages copy; full byte equality ---- */
    {
        uint8_t *src=fresh(size);uint8_t *dst=fresh(size);
        memset(src,0,size);pattern_nonzero(src,pages,device?1024:8);
        uint64_t expected=(pages+ (device?1024:8) -1)/(device?1024:8)*PAGE;
        uint64_t src_hash=hash_bytes(src,size);
        long before=rss_kb();
        uint64_t copied=t2_fixture_sparse_scan(dst,(uint64_t)(uintptr_t)src,size);
        long after=rss_kb();
        int ok=(copied==expected)&&(memcmp(dst,src,size)==0)&&(hash_bytes(src,size)==src_hash);
        emit("sparse_mixed",copied,size,ok);
        if(device)emit_rss("sparse_mixed",after-before);
        /* read-after-write on a skipped page, then re-verify the rest */
        uint8_t *probe=dst+1*PAGE; /* page 1 stays zero (stride>1) */
        int probe_zero=(probe[0]==0&&probe[PAGE-1]==0);
        memset(probe,0x41,PAGE);
        int probe_rw=(probe[0]==0x41&&probe[PAGE-1]==0x41);
        int others_zero=1;
        for(uint64_t i=2;i<8;i++)if(dst[i*PAGE]||dst[i*PAGE+PAGE-1])others_zero=0;
        int rw_ok=probe_zero&&probe_rw&&others_zero;
        emit("read_after_write",copied,size,rw_ok);
        munmap(src,size);munmap(dst,size);
    }
    /* ---- dense: everything copies; accounting equals size ---- */
    {
        uint8_t *src=fresh(size);uint8_t *dst=fresh(size);
        pattern_dense(src,size);
        long before=rss_kb();
        uint64_t copied=t2_fixture_sparse_scan(dst,(uint64_t)(uintptr_t)src,size);
        long after=rss_kb();
        int ok=(copied==size)&&(memcmp(dst,src,size)==0);
        emit("dense",copied,size,ok);
        if(device){
            long delta=after-before;
            emit_rss("dense",delta);
            emit("dense_rss",(uint64_t)(delta>0?delta:0),size,(delta>=(long)(size/1024*3/4)));
        }
        munmap(src,size);munmap(dst,size);
    }
    /* ---- double creation: independent destinations, same source ---- */
    {
        uint8_t *src=fresh(size);uint8_t *a=fresh(size);uint8_t *b=fresh(size);
        memset(src,0,size);pattern_nonzero(src,pages,16);
        uint64_t ca=t2_fixture_sparse_scan(a,(uint64_t)(uintptr_t)src,size);
        uint64_t cb=t2_fixture_sparse_scan(b,(uint64_t)(uintptr_t)src,size);
        int ok=(ca==cb)&&(memcmp(a,src,size)==0)&&(memcmp(b,src,size)==0);
        emit("double_creation",ca,size,ok);
        munmap(src,size);munmap(a,size);munmap(b,size);
    }
    /* ---- copyback: release-path memcpy reproduces the creation-time source ---- */
    {
        uint8_t *src=fresh(size);uint8_t *dst=fresh(size);uint8_t *back=fresh(size);
        memset(src,0,size);pattern_nonzero(src,pages,32);
        uint64_t src_hash=hash_bytes(src,size);
        t2_fixture_sparse_scan(dst,(uint64_t)(uintptr_t)src,size);
        memcpy(back,dst,size); /* transfer_release_locked copyback */
        int ok=(memcmp(back,src,size)==0)&&(hash_bytes(src,size)==src_hash);
        emit("copyback",size,size,ok);
        munmap(src,size);munmap(dst,size);munmap(back,size);
    }
    printf("RESULT failures=%d mode=%s\n",failures,device?"device":"small");fflush(stdout);
    return failures?1:0;
}
