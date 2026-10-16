/* bcdecode_host.c — host-side exact replica of the runtime BC pixel path.
 *
 * The runtime decodes BC blocks with vendor/bcdec (see zero_bc.h) and uploads those exact
 * RGBA bytes; the M6 cache is keyed by sha256 over them, so the host builder must use the
 * same decoder, not a different library. This tool batch-decodes raw level-0 BC payloads:
 *
 *   bcdecode_host <indir> <outdir>
 *
 * For every <indir>/WxH-FMT-IDX.bc it writes <outdir>/WxH-FMT-IDX.rgba (RGBA8, w*h*4 bytes).
 * FMT is the NVN-style hex code (0x41/0x42 BC1, 0x43 BC2, 0x44 BC3). Level-0 only,
 * matching the runtime's i==0 upload path for single-level textures.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <dirent.h>

#define BCDECDEF static inline
#define BCDEC_BC4BC5_PRECISE
#define BCDEC_IMPLEMENTATION
#include "bcdec.h"

static int decode_one(const char *in_path, const char *out_path, unsigned w, unsigned h, unsigned fmt) {
    FILE *fi = fopen(in_path, "rb");
    if (!fi) { fprintf(stderr, "open fail %s\n", in_path); return 1; }
    uint8_t *dst = malloc((size_t)w * h * 4);
    if (!dst) { fclose(fi); return 1; }
    unsigned block = (fmt == 0x41 || fmt == 0x42) ? 8 : 16;
    unsigned nx = (w + 3) / 4, ny = (h + 3) / 4;
    int rc = 0;
    for (unsigned y = 0; y < ny && !rc; y++)
        for (unsigned x = 0; x < nx && !rc; x++) {
            uint8_t bytes[16] = {0};
            if (fread(bytes, 1, block, fi) != block) { fprintf(stderr, "short read %s\n", in_path); rc = 2; break; }
            uint64_t input[2] = {0};
            memcpy(input, bytes, block);
            uint32_t rgba[16];
            int normalized = (fmt >= 0x45 && fmt <= 0x48) ? (int)fmt - 4 : (int)fmt;
            if (normalized == 0x41 || normalized == 0x42) bcdec_bc1(input, rgba, 16);
            else if (normalized == 0x43) bcdec_bc2(input, rgba, 16);
            else if (normalized == 0x44) bcdec_bc3(input, rgba, 16);
            else { fprintf(stderr, "unsupported fmt %x\n", fmt); rc = 3; break; }
            if (normalized == 0x41) for (unsigned i = 0; i < 16; i++) ((uint8_t *)rgba)[i * 4 + 3] = 255;
            for (unsigned dy = 0; dy < 4 && y * 4 + dy < h; dy++)
                for (unsigned dx = 0; dx < 4 && x * 4 + dx < w; dx++)
                    memcpy(dst + ((size_t)(y * 4 + dy) * w + x * 4 + dx) * 4, &rgba[dy * 4 + dx], 4);
        }
    if (!rc) {
        FILE *fo = fopen(out_path, "wb");
        if (!fo || fwrite(dst, 1, (size_t)w * h * 4, fo) != (size_t)w * h * 4) rc = 4;
        if (fo) fclose(fo);
    }
    free(dst);
    fclose(fi);
    return rc;
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s <indir> <outdir>\n", argv[0]); return 64; }
    DIR *d = opendir(argv[1]);
    if (!d) { fprintf(stderr, "opendir fail\n"); return 66; }
    struct dirent *e;
    unsigned n = 0, failed = 0;
    while ((e = readdir(d))) {
        unsigned w, h, fmt;
        long long idx;
        if (sscanf(e->d_name, "%ux%u-%x-%lld.bc", &w, &h, &fmt, &idx) != 4) continue;
        char in_path[1024], out_path[1024];
        snprintf(in_path, sizeof(in_path), "%s/%s", argv[1], e->d_name);
        snprintf(out_path, sizeof(out_path), "%s/%ux%u-%x-%lld.rgba", argv[2], w, h, fmt, idx);
        if (decode_one(in_path, out_path, w, h, fmt)) failed++;
        n++;
    }
    closedir(d);
    printf("DECODED %u failed=%u\n", n - failed, failed);
    return failed ? 1 : 0;
}
