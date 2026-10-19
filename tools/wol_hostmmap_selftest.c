/* wol_hostmmap_selftest.c - driver proving the LD_PRELOAD shim logs big host allocations.
 * Built and run by tools/test_wol_hostmmap_shim.py on the build host only.
 * Allocations are read back through a volatile sink so the compiler cannot
 * elide malloc/memset/free triples (that elision was observed at -O1).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

static volatile unsigned long sink;

__attribute__((noinline)) static void touch(const unsigned char *p, size_t n) {
    unsigned long s = 0;
    for (size_t i = 0; i < n; i += 4096) s += p[i];
    sink += s;
}

int main(void) {
    void *p = mmap(NULL, 6 * 1024 * 1024, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    memset(p, 1, 4096);
    touch(p, 6 * 1024 * 1024);
    void *m = malloc(5 * 1024 * 1024);
    if (!m) { perror("malloc"); return 1; }
    memset(m, 2, 4096);
    touch(m, 5 * 1024 * 1024);
    void *c = calloc(1, 7 * 1024 * 1024);
    if (!c) { perror("calloc"); return 1; }
    touch(c, 7 * 1024 * 1024);
    void *s = malloc(1024);
    if (!s) { perror("small malloc"); return 1; }
    touch(s, 1024);
    free(s);
    free(c);
    free(m);
    if (munmap(p, 6 * 1024 * 1024)) { perror("munmap"); return 1; }
    printf("SELFTEST_OK %lu\n", sink);
    return 0;
}
