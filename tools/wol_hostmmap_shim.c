/*
 * wol_hostmmap_shim.c - bounded host-side allocation logger (diagnostic only).
 *
 * WHY: the per-VMA swap census (evidence/m5-swap-location) found a deterministic
 * 72 MiB zero-filled anonymous mapping, 0.2 MiB resident / 63.9 MiB swapped,
 * present in every run and never touched after the initial load. Nothing in the
 * port's own native tree maps that size directly, so the owner must be named
 * before any release is contemplated. This shim records every host-side
 * mmap/malloc-family request at or above a threshold with caller frames.
 *
 * SAFETY: default OFF - it only exists when the process is started with
 * LD_PRELOAD pointing at this object. It never changes sizes, flags or
 * addresses: every call is forwarded to the real implementation untouched.
 * Reads only its own environment and appends to its own log file.
 *
 * ENV: WOL_HOSTMMAP_LOG  log path (default /mnt/UDISK/hostmmap.log)
 *      WOL_HOSTMMAP_MIN  threshold in bytes (default 16777216 = 16 MiB)
 *
 * LINE: HOSTMMAP ts=<mono_ns> op=<name> pid=<pid> size=<bytes> [extra...] ret=<ptr> frames=<mod+0xoff;...>
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <execinfo.h>
#include <fcntl.h>
#include <malloc.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define WOL_HOSTMMAP_MAX_FRAMES 6
#define WOL_HOSTMMAP_LINE 640

static __thread int wol_shim_busy;
static int wol_shim_ready;
static size_t wol_shim_min = 16u * 1024u * 1024u;
static int wol_shim_fd = -1;

static void *wol_real_mmap;
static void *wol_real_munmap;
static void *wol_real_malloc;
static void *wol_real_calloc;
static void *wol_real_realloc;
static void *wol_real_memalign;
static void *wol_real_posix_memalign;
static void *wol_real_aligned_alloc;

static void wol_shim_init(void) {
    if (wol_shim_ready) return;
    wol_shim_ready = 1;
    const char *path = getenv("WOL_HOSTMMAP_LOG");
    if (!path || !*path) path = "/mnt/UDISK/hostmmap.log";
    const char *min_s = getenv("WOL_HOSTMMAP_MIN");
    if (min_s && *min_s) {
        unsigned long long v = strtoull(min_s, NULL, 0);
        if (v > 0) wol_shim_min = (size_t)v;
    }
    wol_shim_fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
    wol_real_mmap = dlsym(RTLD_NEXT, "mmap");
    wol_real_munmap = dlsym(RTLD_NEXT, "munmap");
    wol_real_malloc = dlsym(RTLD_NEXT, "malloc");
    wol_real_calloc = dlsym(RTLD_NEXT, "calloc");
    wol_real_realloc = dlsym(RTLD_NEXT, "realloc");
    wol_real_memalign = dlsym(RTLD_NEXT, "memalign");
    wol_real_posix_memalign = dlsym(RTLD_NEXT, "posix_memalign");
    wol_real_aligned_alloc = dlsym(RTLD_NEXT, "aligned_alloc");
}

static void wol_frame_append(char *buf, size_t cap, size_t *used, void *pc) {
    Dl_info info;
    int n;
    if (*used + 24 >= cap) return;
    if (pc && dladdr(pc, &info) && info.dli_fname && info.dli_fbase) {
        const char *base = strrchr(info.dli_fname, '/');
        base = base ? base + 1 : info.dli_fname;
        n = snprintf(buf + *used, cap - *used, "%s+0x%llx;", base,
                     (unsigned long long)((uintptr_t)pc - (uintptr_t)info.dli_fbase));
    } else {
        n = snprintf(buf + *used, cap - *used, "?;");
    }
    if (n > 0 && (size_t)n < cap - *used) *used += (size_t)n;
}

static void wol_log(const char *op, size_t size, const void *ret, const char *extra) {
    void *frames[WOL_HOSTMMAP_MAX_FRAMES];
    struct timespec ts;
    char buf[WOL_HOSTMMAP_LINE];
    size_t used = 0;
    int n, count;
    if (wol_shim_fd < 0) return;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    n = snprintf(buf, sizeof buf, "HOSTMMAP ts=%llu op=%s pid=%d size=%zu%s ret=%p frames=",
                 (unsigned long long)ts.tv_sec * 1000000000ull + (unsigned long long)ts.tv_nsec,
                 op, (int)getpid(), size, extra ? extra : "", ret);
    if (n <= 0) return;
    used = (size_t)n < sizeof buf ? (size_t)n : sizeof buf - 1;
    count = backtrace(frames, WOL_HOSTMMAP_MAX_FRAMES);
    for (int i = 0; i < count && (size_t)i < WOL_HOSTMMAP_MAX_FRAMES; i++)
        wol_frame_append(buf, sizeof buf, &used, frames[i]);
    if (used + 2 < sizeof buf) {
        buf[used++] = '\n';
        buf[used] = 0;
    }
    if (write(wol_shim_fd, buf, used) < 0) { /* diagnostic only */ }
}

/* --- mmap family ------------------------------------------------------- */

void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off) {
    void *r;
    size_t size = len;
    void *a = addr;
    int p = prot, f = flags, d = fd;
    off_t o = off;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && size >= wol_shim_min) {
        char extra[96];
        snprintf(extra, sizeof extra, " prot=%#x flags=%#x fd=%d off=%lld", p, f, d, (long long)o);
        wol_shim_busy = 1;
        wol_log("mmap", size, NULL, extra);
        wol_shim_busy = 0;
    }
    if (wol_real_mmap) {
        void *(*fn)(void *, size_t, int, int, int, off_t) = wol_real_mmap;
        r = fn(a, size, p, f, d, o);
    } else {
        long v = syscall(SYS_mmap, a, size, p, f, d, o);
        r = (v == -1) ? MAP_FAILED : (void *)(uintptr_t)v;
    }
    return r;
}

void *mmap64(void *addr, size_t len, int prot, int flags, int fd, off64_t off) {
    return mmap(addr, len, prot, flags, fd, (off_t)off);
}

int munmap(void *addr, size_t len) {
    int r;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && len >= wol_shim_min) {
        wol_shim_busy = 1;
        wol_log("munmap", len, addr, NULL);
        wol_shim_busy = 0;
    }
    if (wol_real_munmap) {
        int (*fn)(void *, size_t) = wol_real_munmap;
        r = fn(addr, len);
    } else {
        r = (int)syscall(SYS_munmap, addr, len);
    }
    return r;
}

/* --- allocation family ------------------------------------------------- */

void *malloc(size_t size) {
    void *r;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && size >= wol_shim_min) {
        wol_shim_busy = 1;
        wol_log("malloc", size, NULL, NULL);
        wol_shim_busy = 0;
    }
    if (wol_real_malloc) {
        void *(*fn)(size_t) = wol_real_malloc;
        r = fn(size);
    } else {
        r = NULL;
        errno = ENOMEM;
    }
    return r;
}

void *calloc(size_t nmemb, size_t size) {
    void *r;
    size_t total = nmemb * size;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && nmemb && size && total / size == nmemb && total >= wol_shim_min) {
        wol_shim_busy = 1;
        wol_log("calloc", total, NULL, NULL);
        wol_shim_busy = 0;
    }
    if (wol_real_calloc) {
        void *(*fn)(size_t, size_t) = wol_real_calloc;
        r = fn(nmemb, size);
    } else {
        r = NULL;
        errno = ENOMEM;
    }
    return r;
}

void *realloc(void *ptr, size_t size) {
    void *r;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && size >= wol_shim_min) {
        wol_shim_busy = 1;
        wol_log("realloc", size, ptr, NULL);
        wol_shim_busy = 0;
    }
    if (wol_real_realloc) {
        void *(*fn)(void *, size_t) = wol_real_realloc;
        r = fn(ptr, size);
    } else {
        r = NULL;
        errno = ENOMEM;
    }
    return r;
}

void *memalign(size_t alignment, size_t size) {
    void *r;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && size >= wol_shim_min) {
        char extra[48];
        snprintf(extra, sizeof extra, " align=%zu", alignment);
        wol_shim_busy = 1;
        wol_log("memalign", size, NULL, extra);
        wol_shim_busy = 0;
    }
    if (wol_real_memalign) {
        void *(*fn)(size_t, size_t) = wol_real_memalign;
        r = fn(alignment, size);
    } else {
        r = NULL;
        errno = ENOMEM;
    }
    return r;
}

int posix_memalign(void **memptr, size_t alignment, size_t size) {
    int r;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && size >= wol_shim_min) {
        char extra[48];
        snprintf(extra, sizeof extra, " align=%zu", alignment);
        wol_shim_busy = 1;
        wol_log("posix_memalign", size, NULL, extra);
        wol_shim_busy = 0;
    }
    if (wol_real_posix_memalign) {
        int (*fn)(void **, size_t, size_t) = wol_real_posix_memalign;
        r = fn(memptr, alignment, size);
    } else {
        r = ENOMEM;
    }
    return r;
}

void *aligned_alloc(size_t alignment, size_t size) {
    void *r;
    if (!wol_shim_ready && !wol_shim_busy) { wol_shim_busy = 1; wol_shim_init(); wol_shim_busy = 0; }
    if (!wol_shim_busy && size >= wol_shim_min) {
        char extra[48];
        snprintf(extra, sizeof extra, " align=%zu", alignment);
        wol_shim_busy = 1;
        wol_log("aligned_alloc", size, NULL, extra);
        wol_shim_busy = 0;
    }
    if (wol_real_aligned_alloc) {
        void *(*fn)(size_t, size_t) = wol_real_aligned_alloc;
        r = fn(alignment, size);
    } else {
        r = NULL;
        errno = ENOMEM;
    }
    return r;
}
