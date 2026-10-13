/* Minimal kmsgrab for the TSPS: reads the active CRTC's framebuffer via the DRM uapi and dumps a PPM.
 * No libdrm: raw ioctls. Run as root while the port owns the display. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <stdint.h>
#include <errno.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>

int main(int argc, char **argv) {
    const char *dev = argc > 1 ? argv[1] : "/dev/dri/card0";
    const char *out = argc > 2 ? argv[2] : "kmsgrab.ppm";
    int fd = open(dev, O_RDWR | O_CLOEXEC);
    if (fd < 0) { perror("open"); return 1; }
    struct drm_mode_card_res res;
    memset(&res, 0, sizeof res);
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)) { perror("res"); return 1; }
    uint32_t crtcs[16];
    memset(crtcs, 0, sizeof crtcs);
    unsigned ncrtc = res.count_crtcs;
    fprintf(stderr, "first call: crtcs=%u fbs=%u conns=%u\n", res.count_crtcs, res.count_fbs, res.count_connectors);
    /* second call: only the crtc array (counts are capacities on input, the others stay NULL/0) */
    struct drm_mode_card_res res2;
    memset(&res2, 0, sizeof res2);
    res2.crtc_id_ptr = (uint64_t)(uintptr_t)crtcs;
    res2.count_crtcs = ncrtc > 16 ? 16 : ncrtc;
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res2)) { printf("res2 errno=%d\n", errno); perror("res2"); return 1; }
    /* dump each CRTC that has a framebuffer (the TSPS has two: HDMI and the DSI panel) */
    unsigned captured = 0;
    for (unsigned c = 0; c < ncrtc && c < 15; c++) {
        struct drm_mode_crtc gc;
        memset(&gc, 0, sizeof gc);
        gc.crtc_id = crtcs[c];
        if (ioctl(fd, DRM_IOCTL_MODE_GETCRTC, &gc) || !gc.fb_id) continue;
        char name[256];
        snprintf(name, sizeof name, "%s.crtc%u.ppm", out, c);
        uint32_t fb = gc.fb_id;
        fprintf(stderr, "crtc%u fb=%u -> %s\n", c, fb, name);
        struct drm_mode_fb_cmd fbc;
    memset(&fbc, 0, sizeof fbc);
    fbc.fb_id = fb;
    if (ioctl(fd, DRM_IOCTL_MODE_GETFB, &fbc)) { perror("getfb"); return 1; }
    unsigned w = fbc.width, h = fbc.height, bpp = (fbc.bpp + 7) / 8, pitch = fbc.pitch;
    fprintf(stderr, "%ux%u bpp=%u pitch=%u handle=%u\n", w, h, bpp, pitch, fbc.handle);
    struct drm_prime_handle ph;
    memset(&ph, 0, sizeof ph);
    ph.handle = fbc.handle;
    ph.flags = O_RDWR | O_CLOEXEC;
    if (ioctl(fd, DRM_IOCTL_PRIME_HANDLE_TO_FD, &ph)) { perror("prime2fd"); return 1; }
    size_t len = (size_t)pitch * h;
    uint8_t *map = mmap(NULL, len, PROT_READ, MAP_SHARED, ph.fd, 0);
    if (map == MAP_FAILED) { perror("mmap"); return 1; }
    FILE *o = fopen(name, "wb");
    if (!o) { perror("fopen"); return 1; }
    fprintf(o, "P6\n%u %u\n255\n", w, h);
    for (unsigned y = 0; y < h; y++)
        for (unsigned x = 0; x < w; x++) {
            uint8_t *p = map + (size_t)y * pitch + (size_t)x * bpp;
            uint8_t rgb[3];
            rgb[0] = p[2]; rgb[1] = p[1]; rgb[2] = p[0]; /* XRGB8888 little-endian bytes B,G,R,X */
            fwrite(rgb, 1, 3, o);
        }
    fclose(o);
        captured++;
    }
    if (!captured) return 2;
    return 0;
}
