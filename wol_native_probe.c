/* Experimental, bounded, single-thread AArch64/Horizon execution probe.
 * Original guest code is patched ONLY in anonymous mappings. Never writes inputs.
 * Minimal SM Initialize IPC only; no NVN/audio/game compatibility claim.
 * Fail closed on unsupported operations; virtual kernel settings are not measurements.
 * Diagnostic signal logging is prototype-only, not production async-signal safe.
 */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <sys/mman.h>
#include <ucontext.h>
#include <sys/syscall.h>
#include <linux/futex.h>
#include <sys/random.h>
#include <limits.h>

struct region { uintptr_t base; size_t size; unsigned type, perm; char name[32]; };
struct trap { uintptr_t pc; unsigned kind, arg; };
struct meminfo { uint64_t base,size; uint32_t type,attr,perm,ipc_ref,device_ref,padding; };
static struct region regions[64];
static unsigned nr,nt,loaded_modules;
static struct trap traps[8192];
static uintptr_t guest_tls,guest_tpidr_el0;
static unsigned calls;
static uintptr_t span_end;
/* Minimum SDK bootstrap thread ABI observed in this exact WoL SDK.
 * Not a general ThreadType implementation or evidence that thread services work. */
static void bootstrap_thread(void) {
    uintptr_t thread=guest_tls+0x400;
    *(uintptr_t *)(guest_tls+0x1f8)=thread;
    *(uint32_t *)(thread+0x1b8)=0x100;
}

static void add_region(uintptr_t base,size_t size,unsigned type,unsigned perm,const char *name) {
    if(nr>=64) { fputs("region limit\n",stderr); exit(71); }
    regions[nr]=(struct region){base,size,type,perm,{0}};
    snprintf(regions[nr].name,32,"%s",name); ++nr;
}
static int contains(uintptr_t ptr,size_t size) {
    for(unsigned i=0;i<nr;i++) if(ptr>=regions[i].base && size<=regions[i].size && ptr-regions[i].base<=regions[i].size-size) return 1;
    return 0;
}
static int writable(uintptr_t ptr,size_t size) {
    for(unsigned i=0;i<nr;i++) if((regions[i].perm&2) && ptr>=regions[i].base && size<=regions[i].size && ptr-regions[i].base<=regions[i].size-size) return 1;
    return 0;
}
static void locate(uintptr_t pc,char *buf,size_t size) {
    for(unsigned i=0;i<nr;i++) if(pc>=regions[i].base && pc-regions[i].base<regions[i].size) { snprintf(buf,size,"%s+0x%lx",regions[i].name,(unsigned long)(pc-regions[i].base)); return; }
    snprintf(buf,size,"host/unknown:0x%lx",(unsigned long)pc);
}
static void query(uintptr_t addr,struct meminfo *info) {
    memset(info,0,sizeof(*info));
    uintptr_t low=0,high=((uintptr_t)1<<39);
    for(unsigned i=0;i<nr;i++) {
        struct region *r=&regions[i];
        if(addr>=r->base && addr-r->base<r->size) { info->base=r->base; info->size=r->size; info->type=r->type; info->perm=r->perm; return; }
        if(r->base>addr && r->base<high) high=r->base;
        if(r->base+r->size<=addr && r->base+r->size>low) low=r->base+r->size;
    }
    info->base=low; info->size=high-low;
}
static void stop(const char *reason,ucontext_t *uc,unsigned arg,int status) {
    char where[96]; locate(uc->uc_mcontext.pc,where,sizeof(where));
    dprintf(1,"STOP %s svc=0x%x pc=%s x0=0x%llx x1=0x%llx x2=0x%llx x3=0x%llx lr=0x%llx calls=%u\n",reason,arg,where,uc->uc_mcontext.regs[0],uc->uc_mcontext.regs[1],uc->uc_mcontext.regs[2],uc->uc_mcontext.regs[3],uc->uc_mcontext.regs[30],calls);
    uintptr_t frame=uc->uc_mcontext.regs[29];
    for(unsigned i=0;i<16 && !(frame&7) && contains(frame,16);i++) {
        uintptr_t *p=(uintptr_t*)frame; char caller[96]; locate(p[1],caller,sizeof(caller));
        dprintf(1,"FRAME index=%u caller=%s fp=0x%lx\n",i,caller,(unsigned long)frame);
        if(p[0]<=frame) break;
        frame=p[0];
    }
    _exit(status);
}
static unsigned sm_connected,sm_initialized;
static uint32_t word32(const uint8_t *p) { uint32_t x; memcpy(&x,p,4); return x; }
static void putword(uint8_t *p,uint32_t x) { memcpy(p,&x,4); }
/* CMIF layout checked against legacy_runtime's GPL source native/ipc.h.
 * Deliberately narrower: one SM session, Initialize only, no fake service replies. */
static void sm_request(uint64_t handle,ucontext_t *uc) {
    if(handle!=0x200 || !sm_connected) stop("UNKNOWN_IPC_HANDLE",uc,0x21,70);
    uint8_t *b=(uint8_t*)guest_tls;
    if(!writable(guest_tls,256)) stop("INVALID_IPC_BUFFER",uc,0x21,71);
    uint32_t h0=word32(b),h1=word32(b+4),special=0;
    size_t cursor=8;
    if(h0>>16 || ((h1>>10)&15)) stop("UNSUPPORTED_IPC_DESCRIPTORS",uc,0x21,70);
    if(h1>>31) { special=word32(b+cursor); cursor+=4; if(special&1) cursor+=8; }
    if(special&~1U) stop("UNSUPPORTED_IPC_HANDLES",uc,0x21,70);
    size_t aligned=(cursor+15)&~15UL, raw=(h1&1023)*4;
    if(raw>256-cursor || aligned+16>cursor+raw || word32(b+aligned)!=0x49434653 || word32(b+aligned+4)>1) stop("INVALID_CMIF",uc,0x21,71);
    unsigned type=h0&65535,command=word32(b+aligned+8),token=word32(b+aligned+12);
    size_t payload=cursor+raw-aligned-16;
    dprintf(1,"IPC endpoint=sm type=%u command=%u payload=%zu pid=%u\n",type,command,payload,special&1);
    if(type!=4 && type!=6) stop("UNSUPPORTED_IPC_TYPE",uc,0x21,70);
    if(command==0) {
        if(!(special&1) || payload<8 || sm_initialized) stop("INVALID_SM_INITIALIZE",uc,0x21,71);
        sm_initialized=1;
        memset(b,0,256); putword(b+4,8); putword(b+16,0x4f434653); putword(b+28,token);
        dprintf(1,"SM_INITIALIZE result=success\n"); return;
    }
    if(command==1) {
        if(!sm_initialized || payload<8) stop("INVALID_SM_GET_SERVICE",uc,0x21,71);
        char service[9]={0}; memcpy(service,b+aligned+16,8);
        dprintf(1,"GET_SERVICE name=%s implementation=absent\n",service);
        stop("UNIMPLEMENTED_SERVICE",uc,0x21,70);
    }
    stop("UNSUPPORTED_SM_COMMAND",uc,0x21,70);
}
static void handler(int sig,siginfo_t *si,void *context) {
    (void)si;
    ucontext_t *uc=context;
    if(sig!=SIGTRAP) { stop(sig==SIGALRM?"WALL_LIMIT":"GUEST_FAULT",uc,(unsigned)sig,71); }
    struct trap *t=NULL;
    for(unsigned i=0;i<nt;i++) if(traps[i].pc==uc->uc_mcontext.pc) { t=&traps[i]; break; }
    if(!t) stop("UNREGISTERED_TRAP",uc,0,71);
    unsigned long long *x=uc->uc_mcontext.regs;
    if(t->kind==2) { unsigned reg=t->arg&31; if(reg!=31) x[reg]=(t->arg&256)?guest_tls:guest_tpidr_el0; uc->uc_mcontext.pc+=4; return; }
    if(t->kind==3) { uintptr_t value=t->arg==31?0:x[t->arg]; if(value && !writable(value,1)) stop("INVALID_TLS_WRITE",uc,0,71); guest_tpidr_el0=value; uc->uc_mcontext.pc+=4; return; }
    ++calls;
    char where[96]; locate(t->pc,where,sizeof(where));
    dprintf(1,"SVC call=%u id=0x%x pc=%s\n",calls,t->arg,where);
    switch(t->arg) {
    case 0x6: { /* QueryMemory: x0 out MemoryInfo, x2 queried address, x1 output page info. */
        if(!writable(x[0],sizeof(struct meminfo))) stop("BAD_GUEST_POINTER",uc,t->arg,71);
        query(x[2],(struct meminfo *)(uintptr_t)x[0]); x[0]=0; x[1]=0; break;
    }
    case 0x1f: { /* ConnectToNamedPort: admitted virtual SM endpoint only. */
        char port[13]={0}; unsigned n;
        for(n=0;n<12;n++) { if(!contains(x[1]+n,1)) stop("INVALID_PORT_NAME",uc,t->arg,71); port[n]=*(char*)(uintptr_t)(x[1]+n); if(!port[n]) break; }
        if(n==12) stop("PORT_NAME_TOO_LONG",uc,t->arg,71);
        dprintf(1,"CONNECT port=%s\n",port);
        if(strcmp(port,"sm:") || sm_connected) stop("UNSUPPORTED_NAMED_PORT",uc,t->arg,70);
        sm_connected=1; x[0]=0; x[1]=0x200; break;
    }
    case 0x21: sm_request(x[0],uc); x[0]=0; break;
    case 0x25: /* GetThreadId: single bootstrap/main thread. */
        if((uint32_t)x[1]!=0x100 && (uint32_t)x[1]!=0xffff8000) stop("UNKNOWN_THREAD_HANDLE",uc,t->arg,70);
        x[0]=0; x[1]=1; break;
    case 0xc: /* GetThreadPriority: only configured bootstrap/main thread exists. */
        if((uint32_t)x[1]!=0x100 && (uint32_t)x[1]!=0xffff8000) stop("UNKNOWN_THREAD_HANDLE",uc,t->arg,70);
        x[0]=0; x[1]=44; break;
    case 0x1d: { /* SignalProcessWideKey: wake mapped futex; no guest wait/thread support yet. */
        if((x[0]&3) || !contains(x[0],4)) stop("BAD_GUEST_KEY",uc,t->arg,71);
        int count=(int32_t)x[1];
        long woke=syscall(SYS_futex,(void*)(uintptr_t)x[0],FUTEX_WAKE_PRIVATE,count<0?INT_MAX:count,NULL,NULL,0);
        if(woke<0) stop("HOST_FUTEX_WAKE_FAILED",uc,t->arg,71);
        x[0]=0; break;
    }
    case 0x29: { /* Kernel trap ABI: Result in x0, value in x1.
        * SDK wrapper saves the caller out pointer on SP before SVC, then stores x1.
        * Verified at this SDK+0xa9e04..0xa9e18; do not confuse public function ABI. */
        uint64_t id=x[1],value=0;
        dprintf(1,"GETINFO type=%llu handle=0x%llx sub=%llu\n",x[1],x[2],x[3]);
        if((id!=11 && x[3]!=0) || (id==11 && x[3]>3)) stop("UNSUPPORTED_GETINFO_SUBID",uc,t->arg,70);
        switch(id) {
        case 0: value=0xff; break; /* virtual CPU permission mask, not physical host */
        case 1: value=UINT64_MAX; break;
        case 2: value=0x20000000; break;
        case 3: value=0x10000000; break;
        case 4: value=0x40000000; break;
        case 5: value=0x10000000; break;
        case 6: value=963ULL*1024*1024; break; /* configured budget, not measured RSS */
        case 7: value=span_end>0x08000000?span_end-0x08000000:0; break;
        case 11:
            if(getrandom(&value,sizeof(value),0)!=sizeof(value)) stop("HOST_ENTROPY_FAILED",uc,t->arg,71);
            break;
        case 12: value=0x08000000; break;
        case 13: value=0x78001000-0x08000000; break;
        case 14: value=0x60000000; break;
        case 15: value=8*1024*1024; break;
        default: stop("UNSUPPORTED_GETINFO_TYPE",uc,t->arg,70);
        }
        x[0]=0; x[1]=value; break;
    }
    case 0x1e: { /* Horizon system tick frequency is 19.2 MHz. */
        struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts);
        x[0]=(uint64_t)ts.tv_sec*19200000 + (uint64_t)ts.tv_nsec*192/10000; break;
    }
    case 0x27: /* OutputDebugString */
        if(x[1]>4096 || !contains(x[0],x[1])) stop("BAD_GUEST_DEBUG_STRING",uc,t->arg,71);
        if(write(1,(void *)(uintptr_t)x[0],x[1])<0) { stop("DEBUG_WRITE_FAILED",uc,t->arg,71); }
        x[0]=0; break;
    case 0x7: stop("GUEST_EXIT_PROCESS",uc,t->arg,72); break;
    case 0x26: stop("GUEST_BREAK",uc,t->arg,73); break;
    default: stop("UNSUPPORTED_SVC",uc,t->arg,70);
    }
    uc->uc_mcontext.pc+=4;
}
static void install(void) {
    void *alt=mmap(NULL,65536,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(alt==MAP_FAILED) { perror("altstack"); exit(71); }
    stack_t stack={.ss_sp=alt,.ss_size=65536}; if(sigaltstack(&stack,NULL)) { perror("sigaltstack"); exit(71); }
    struct sigaction sa={.sa_sigaction=handler,.sa_flags=SA_SIGINFO|SA_ONSTACK}; sigemptyset(&sa.sa_mask);
    int sigs[]={SIGTRAP,SIGSEGV,SIGBUS,SIGILL,SIGALRM};
    for(unsigned i=0;i<sizeof(sigs)/sizeof(sigs[0]);i++) if(sigaction(sigs[i],&sa,NULL)) { perror("sigaction"); exit(71); }
}
static unsigned patch(uint32_t *words,size_t bytes) {
    unsigned before=nt;
    for(size_t i=0;i<bytes/4;i++) {
        unsigned w=words[i],kind=0,arg=0;
        if((w&0xffe0001f)==0xd4000001) { kind=1; arg=(w>>5)&65535; }
        if((w&0xffffffe0)==0xd53bd040 || (w&0xffffffe0)==0xd53bd060) { kind=2; arg=(w&31)|(((w&0xffffffe0)==0xd53bd060)?256:0); }
        if((w&0xffffffe0)==0xd51bd040) { kind=3; arg=w&31; }
        if(kind) { if(nt==8192) exit(71); traps[nt]=(struct trap){(uintptr_t)&words[i],kind,arg}; words[i]=0xd4200000|((nt+1)<<5); nt++; }
    }
    __builtin___clear_cache((char*)words,(char*)words+bytes);
    return nt-before;
}
static void *map_fixed(uintptr_t addr,size_t bytes) {
    bytes=(bytes+4095)&~4095UL;
    void *p=mmap((void*)addr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    if(p==MAP_FAILED || (uintptr_t)p!=addr) { perror("mmap fixed"); exit(71); }
    return p;
}
static void read_segment(const char *root,const char *module,const char *name,uintptr_t where,size_t bytes) {
    char path[4096]; snprintf(path,sizeof(path),"%s/%s.%s.seg",root,module,name);
    FILE *f=fopen(path,"rb"); if(!f) { perror(path); exit(71); }
    if(fread((void*)where,1,bytes,f)!=bytes || fgetc(f)!=EOF) { fputs("segment length mismatch\n",stderr); exit(71); } fclose(f);
}
__attribute__((noreturn)) static void enter(uintptr_t entry,uintptr_t stack) {
    __asm__ volatile("mov x9,%0\nmov sp,%1\nmov x0,xzr\nmov x1,#0x100\nbr x9"::"r"(entry),"r"(stack):"x0","x1","x9","memory");
    __builtin_unreachable();
}
static int selftest(const char *name) {
    uintptr_t addr=0x10000000;
    uint32_t *code=map_fixed(addr,4096);
    add_region(addr,4096,3,5,"test-code");
    guest_tls=(uintptr_t)map_fixed(0x20000000,4096); add_region(guest_tls,4096,4,3,"test-tls");
    code[1]=0xd65f03c0; /* RET */
    size_t code_bytes=8;
    bootstrap_thread();
    if(!strcmp(name,"tick")) code[0]=0xd4000001|(0x1e<<5);
    else if(!strcmp(name,"getinfo") || !strcmp(name,"entropy") || !strcmp(name,"priority") || !strcmp(name,"threadid")) {
        code[0]=0xaa0003e9; /* mov x9,x0 */
        code[1]=0xd4000001|((!strcmp(name,"priority")?0xc:(!strcmp(name,"threadid")?0x25:0x29))<<5);
        code[2]=0xf9000121; /* str x1,[x9] */
        code[3]=0xd65f03c0;
        code_bytes=16;
    }
    else if(!strncmp(name,"sm-",3)) {
        code[0]=0xaa0003e9; /* preserve pointer */
        code[1]=0xd4000001|(0x1f<<5);
        if(!strcmp(name,"sm-connect")) {
            code[2]=0xf9000121; code[3]=0xd65f03c0; code_bytes=16;
        } else {
            code[2]=0xaa0103e0; /* mov x0,x1 returned handle */
            code[3]=0xd4000001|(0x21<<5); code[4]=0xd65f03c0; code_bytes=20;
            uint8_t *b=(uint8_t*)guest_tls;
            putword(b,4); putword(b+4,0x80000000U|10); putword(b+8,1);
            putword(b+32,!strcmp(name,"sm-malformed")?0:0x49434653);
            putword(b+44,0x1234);
        }
        memcpy((void*)(guest_tls+0x800),"sm:",4);
    }
    else if(!strcmp(name,"tls-thread")) {
        code[0]=0xd53bd060;
        code[1]=0xf9400000|((0x1f8/8)<<10);
        code[2]=0xb9400000|((0x1b8/4)<<10);
        code[3]=0xd65f03c0;
        code_bytes=16;
    }
    else if(!strcmp(name,"tls")) code[0]=0xd53bd060; /* MRS x0,TPIDRRO_EL0 */
    else if(!strcmp(name,"tls-zero")) {
        code[0]=0xd51bd05f; /* MSR TPIDR_EL0,xzr */
        code[1]=0xd53bd040; /* MRS x0,TPIDR_EL0 */
        code[2]=0xd53bd061; /* MRS x1,TPIDRRO_EL0 */
        code[3]=0xf9000121; /* str x1,[x9] */
        code[4]=0xd65f03c0;
        /* Preserve caller info pointer in x9. */
        memmove(code+1,code,20); code[0]=0xaa0003e9; code_bytes=24;
    }
    else if(!strcmp(name,"unknown")) code[0]=0xd4000001|(0x7f<<5);
    else if(!strcmp(name,"query") || !strcmp(name,"query-readonly")) code[0]=0xd4000001|(6<<5);
    else if(!strcmp(name,"signal")) code[0]=0xd4000001|(0x1d<<5);
    else return 74;
    patch(code,code_bytes); if(mprotect(code,4096,PROT_READ|PROT_EXEC)) return 75;
    struct meminfo *info=(struct meminfo*)guest_tls;
    int entropy=!strcmp(name,"entropy");
    int priority=!strcmp(name,"priority");
    int threadid=!strcmp(name,"threadid");
    int sm=!strncmp(name,"sm-",3);
    uint64_t out=((uint64_t(*)(void*,uintptr_t,uintptr_t,uintptr_t))code)(!strcmp(name,"query-readonly")?(void*)addr:(void*)info,sm?guest_tls+0x800:(entropy?11:((priority||threadid)?0x100:0)),addr,entropy?2:0);
    if(!strcmp(name,"sm-connect") && (out || info->base!=0x200)) return 76;
    if(!strcmp(name,"sm-init") && (out || !sm_initialized || word32((uint8_t*)guest_tls+16)!=0x4f434653 || word32((uint8_t*)guest_tls+28)!=0x1234)) return 76;
    if(priority && (out || info->base!=44)) return 76;
    if(threadid && (out || info->base!=1)) return 76;
    if(!strcmp(name,"tls-zero") && (out || info->base!=guest_tls)) return 76;
    if(entropy && (out || !info->base)) return 76;
    if(!strcmp(name,"tick") && !out) return 76;
    if(!strcmp(name,"signal") && out) return 76;
    if(!strcmp(name,"getinfo") && (out || info->base!=0xff)) return 76;
    if(!strcmp(name,"tls") && out!=guest_tls) return 76;
    if(!strcmp(name,"tls-thread") && out!=0x100) return 76;
    if(!strcmp(name,"query") && (out || info->base!=addr || info->size!=4096 || info->type!=3)) return 76;
    printf("SELFTEST PASS %s\n",name); return 0;
}
int main(int argc,char **argv) {
    setbuf(stdout,NULL); install(); alarm(20);
    if(argc==3 && !strcmp(argv[1],"--selftest")) return selftest(argv[2]);
    if(argc!=3) { fputs("usage: wol-native-probe SEGMENT_ROOT LAYOUT\n",stderr); return 64; }
    FILE *layout=fopen(argv[2],"r"); if(!layout) { perror("layout"); return 66; }
    char name[32]; unsigned long base,text,ro_addr,ro,data_addr,data,bss; uintptr_t entry=0;
    while(fscanf(layout,"%31s %lx %lx %lx %lx %lx %lx %lx",name,&base,&text,&ro_addr,&ro,&data_addr,&data,&bss)==8) {
        size_t span=(data_addr+data+bss+4095)&~4095UL;
        map_fixed(base,span);
        add_region(base,(text+4095)&~4095UL,3,5,name);
        add_region(base+ro_addr,(ro+4095)&~4095UL,3,1,name);
        add_region(base+data_addr,(data+bss+4095)&~4095UL,3,3,name);
        loaded_modules++;
        read_segment(argv[1],name,"text",base,text); read_segment(argv[1],name,"rodata",base+ro_addr,ro); read_segment(argv[1],name,"data",base+data_addr,data);
        unsigned patched=patch((uint32_t*)base,text);
        if(mprotect((void*)base,(text+4095)&~4095UL,PROT_READ|PROT_EXEC)) { perror("mprotect text"); return 71; }
        if(mprotect((void*)(base+ro_addr),(ro+4095)&~4095UL,PROT_READ)) { perror("mprotect rodata"); return 71; }
        printf("MAP module=%s base=0x%lx span=%zu patched=%u\n",name,base,span,patched);
        if(!strcmp(name,"rtld")) entry=base;
        if(base+span>span_end) span_end=base+span;
    }
    fclose(layout); if(!entry) return 66;
    uintptr_t stack=(uintptr_t)map_fixed(0x60000000,8*1024*1024); add_region(stack,8*1024*1024,11,3,"guest-stack");
    guest_tls=(uintptr_t)map_fixed(0x78000000,4096); add_region(guest_tls,4096,4,3,"guest-tls");
    bootstrap_thread();
    printf("ENTER original-rtld=0x%lx modules=%u trap-sites=%u guest-tls=0x%lx execution=real-aarch64 graphics=absent\n",(unsigned long)entry,loaded_modules,nt,(unsigned long)guest_tls);
    enter(entry,stack+8*1024*1024-16);
}
