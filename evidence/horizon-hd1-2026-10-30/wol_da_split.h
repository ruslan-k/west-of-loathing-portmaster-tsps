/* H-D1 (roadmap 25.4): default-OFF, DrawArrays-only CPU+wall stage ledger.
 *
 * Reuses the existing NPS_* boundaries inside nvn_render_draw_inner() instead of adding a
 * second profiler. Per-span start marks keep the spans exactly as non-overlapping as they
 * already were; only the clock source (CLOCK_THREAD_CPUTIME_ID) and the DrawArrays record
 * filter are new. No GL call, allocation, discard or shader work is added inside a span.
 *
 * shortcut: one wall + one CPU clock read per span start and end (~28 reads per frame at
 * three draws), so the profiler itself costs ~0.3% of a frame; that is inside the 5% budget
 * from the roadmap but means the flag is diagnostic, never a shipping default.
 */
#ifndef WOL_DA_SPLIT_H
#define WOL_DA_SPLIT_H
#include <stdint.h>
#include <time.h>

/* One slot per NPS_* span plus the enclosing whole-draw span. Keep in sync with nvn_queue.h. */
#define WOL_DA_STAGES 11

struct wol_da_state {
    unsigned configured, on, active;
    uint64_t wall[WOL_DA_STAGES], cpu[WOL_DA_STAGES], calls[WOL_DA_STAGES];
    uint64_t w0[WOL_DA_STAGES], c0[WOL_DA_STAGES];
    /* Enclosing draw interval has its own slots: it must never alias NPS_SUBMIT, which is
     * stage 10 and would otherwise overwrite the draw-entry timestamp. */
    uint64_t draw_wall_t0, draw_cpu_t0;
    uint64_t total_wall, total_cpu, draws, windows;
};

#ifdef WOL_DA_TEST_CLOCK
/* Host test injects the clock so the arithmetic is checked without depending on real time. */
static uint64_t wol_da_fake_clock;
static inline uint64_t wol_da_wall_now(void){return wol_da_fake_clock;}
static inline uint64_t wol_da_cpu_now(void){return wol_da_fake_clock;}
#else
static inline uint64_t wol_da_wall_now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
    return (uint64_t)t.tv_sec*1000000000ULL+(uint64_t)t.tv_nsec;}
static inline uint64_t wol_da_cpu_now(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
    return (uint64_t)t.tv_sec*1000000000ULL+(uint64_t)t.tv_nsec;}
#endif

static inline void wol_da_mark(struct wol_da_state *s, unsigned k) {
    if(!s->active || k >= WOL_DA_STAGES)return;
    s->w0[k]=wol_da_wall_now();s->c0[k]=wol_da_cpu_now();
}
static inline void wol_da_close(struct wol_da_state *s, unsigned k) {
    if(!s->active || k >= WOL_DA_STAGES)return;
    uint64_t w=wol_da_wall_now(),c=wol_da_cpu_now();
    s->wall[k]+=w-s->w0[k];s->cpu[k]+=c-s->c0[k];s->calls[k]++;
}
static inline void wol_da_open_draw(struct wol_da_state *s) {
    if(!s->on)return;
    s->active=1;s->draws++;
    s->draw_wall_t0=wol_da_wall_now();s->draw_cpu_t0=wol_da_cpu_now();
}
static inline void wol_da_close_draw(struct wol_da_state *s) {
    if(!s->active)return;
    s->active=0;
    s->total_wall+=wol_da_wall_now()-s->draw_wall_t0;
    s->total_cpu+=wol_da_cpu_now()-s->draw_cpu_t0;
}
/* CPU the bracketed stages do not explain; printing it keeps the ledger honest instead of
 * implying the stages sum to the whole draw. */
static inline uint64_t wol_da_residual_cpu(const struct wol_da_state *s) {
    uint64_t sum=0;
    for(unsigned k=0;k<WOL_DA_STAGES;k++)sum+=s->cpu[k];   /* all stages, NPS_SUBMIT included */
    return s->total_cpu>sum?s->total_cpu-sum:0;
}
static inline void wol_da_reset(struct wol_da_state *s) {
    for(unsigned k=0;k<WOL_DA_STAGES;k++){s->wall[k]=s->cpu[k]=s->calls[k]=s->w0[k]=s->c0[k]=0;}
    s->draw_wall_t0=s->draw_cpu_t0=0;
    s->total_wall=s->total_cpu=s->draws=s->windows=0;
}
#endif
