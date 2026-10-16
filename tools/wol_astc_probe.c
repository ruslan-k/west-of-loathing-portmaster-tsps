/* wol_astc_probe_gbm5.c — ASTC acceptance probe (final form).
 *
 * GBM + pbuffer, no window/scanout. Uploads ASTC 6x6 payloads for 64x64 and 96x96,
 * renders each at its own size and reads it back via PPM for offline comparison with
 * the astcenc reference decode. Prints PROBE_* lines.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <dlfcn.h>
#include <EGL/egl.h>
#include <GLES2/gl2.h>

#include "astc_data.h"
#include "astc_data_96.h"

#define ASTC_6x6_FMT 0x93B4 /* GL_COMPRESSED_RGBA_ASTC_6x6_KHR (0x93B0 is 4x4) */
#define EGL_PLATFORM_GBM_KHR 0x31D7

typedef EGLDisplay (*PFNEGLGETPLATFORMDISPLAYEXTPROC)(EGLenum platform, void *native_display, const EGLint *attrib_list);
typedef void *(*PFNGBMCREATEDEVICE)(int fd);

extern void glTexStorage2D(GLenum target, GLsizei levels, GLenum internalformat, GLsizei width, GLsizei height);
extern void glCompressedTexSubImage2D(GLenum target, GLint level, GLint xoffset, GLint yoffset,
                                      GLsizei width, GLsizei height, GLenum format, GLsizei imageSize, const void *data);

static GLuint make_shader(GLenum type, const char *src) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, NULL);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[512];
        glGetShaderInfoLog(s, sizeof(log), NULL, log);
        printf("PROBE_SHADER_ERROR type=0x%x log=%s\n", type, log);
        exit(10);
    }
    return s;
}

static int fail(const char *stage, unsigned e) {
    printf("PROBE_%s err=0x%x\n", stage, e);
    printf("PROBE_RESULT ok=0 stage=%s\n", stage);
    return 1;
}

static unsigned drain_errors(const char *where) {
    unsigned last = 0, e;
    int n = 0;
    while ((e = (unsigned)glGetError()) != 0 && n < 16) { last = e; n++; }
    if (n) printf("PROBE_DRAIN at=%s errors=%d last=0x%x\n", where, n, last);
    return last;
}

/* Render one texture over the full pbuffer and dump it as PPM at its own size. */
static int render_and_dump(GLuint tex, int w, int h, const char *ppm_path) {
    glBindTexture(GL_TEXTURE_2D, tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    static const char *vs =
        "attribute vec2 p; varying vec2 uv;"
        "void main(){ uv = (p + 1.0) * 0.5; gl_Position = vec4(p, 0.0, 1.0); }";
    static const char *fs =
        "precision mediump float; varying vec2 uv; uniform sampler2D t;"
        "void main(){ gl_FragColor = texture2D(t, uv); }";
    GLuint v = make_shader(GL_VERTEX_SHADER, vs);
    GLuint f = make_shader(GL_FRAGMENT_SHADER, fs);
    GLuint prog = glCreateProgram();
    glAttachShader(prog, v);
    glAttachShader(prog, f);
    glLinkProgram(prog);
    GLint linked = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &linked);
    if (!linked) {
        char log[512];
        glGetProgramInfoLog(prog, sizeof(log), NULL, log);
        printf("PROBE_LINK_ERROR log=%s\n", log);
        return -1;
    }
    glUseProgram(prog);
    glUniform1i(glGetUniformLocation(prog, "t"), 0);
    static const float quad[] = { -1, -1,  1, -1,  -1, 1,   -1, 1,  1, -1,  1, 1 };
    GLint pa = glGetAttribLocation(prog, "p");
    glVertexAttribPointer((GLuint)pa, 2, GL_FLOAT, GL_FALSE, 0, quad);
    glEnableVertexAttribArray((GLuint)pa);
    glViewport(0, 0, w, h);
    glClearColor(0.f, 0.f, 0.f, 1.f);
    glClear(GL_COLOR_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLES, 0, 6);

    static unsigned char pix[96 * 96 * 4];
    glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, pix);
    unsigned rb_err = (unsigned)glGetError();
    unsigned long sum = 0, sr = 0, sg = 0, sb = 0;
    for (long i = 0; i < (long)w * h * 4; i++) sum += pix[i];
    unsigned long px = (unsigned long)w * h;
    for (unsigned long i = 0; i < px; i++) { sr += pix[i * 4]; sg += pix[i * 4 + 1]; sb += pix[i * 4 + 2]; }
    printf("PROBE_READBACK src=%dx%d err=0x%x sum=%lu mean_r=%lu mean_g=%lu mean_b=%lu\n",
           w, h, rb_err, sum, sr / px, sg / px, sb / px);
    FILE *fp = fopen(ppm_path, "wb");
    if (fp) {
        fprintf(fp, "P6\n%d %d\n255\n", w, h);
        for (unsigned long i = 0; i < px; i++) fwrite(&pix[i * 4], 1, 3, fp);
        fclose(fp);
        printf("PROBE_PPM %s\n", ppm_path);
    }
    return (int)rb_err;
}

int main(int argc, char **argv) {
    int want_version = (argc > 1 && atoi(argv[1]) == 3) ? 3 : 2;

    int card = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
    if (card < 0) { perror("open card0"); return fail("CARD_OPEN", 0); }
    void *gbm_lib = dlopen("libgbm.so.1", RTLD_NOW);
    if (!gbm_lib) { printf("PROBE_GBM dlopen=%s\n", dlerror()); return fail("GBM_DLOPEN", 0); }
    PFNGBMCREATEDEVICE gbm_create_device = (PFNGBMCREATEDEVICE)dlsym(gbm_lib, "gbm_create_device");
    if (!gbm_create_device) return fail("GBM_SYMBOL", 0);
    void *gbm = gbm_create_device(card);
    if (!gbm) return fail("GBM_CREATE_DEVICE", 0);

    PFNEGLGETPLATFORMDISPLAYEXTPROC get_platform_display =
        (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
    if (!get_platform_display) return fail("EGL_GET_PLATFORM_PROC", 0);
    EGLDisplay dpy = get_platform_display(EGL_PLATFORM_GBM_KHR, gbm, NULL);
    if (dpy == EGL_NO_DISPLAY) return fail("EGL_GBM_NO_DISPLAY", eglGetError());
    EGLint maj = 0, min = 0;
    if (!eglInitialize(dpy, &maj, &min)) return fail("EGL_INITIALIZE", eglGetError());
    if (!eglBindAPI(EGL_OPENGL_ES_API)) return fail("EGL_BIND_API", eglGetError());
    EGLint attrs[] = {
        EGL_SURFACE_TYPE,    EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
        EGL_NONE
    };
    EGLConfig cfg;
    EGLint n = 0;
    if (!eglChooseConfig(dpy, attrs, &cfg, 1, &n) || n != 1) return fail("EGL_CHOOSE_CONFIG", eglGetError());
    EGLint pba[] = { EGL_WIDTH, 96, EGL_HEIGHT, 96, EGL_NONE };
    EGLSurface surf = eglCreatePbufferSurface(dpy, cfg, pba);
    if (surf == EGL_NO_SURFACE) return fail("EGL_PBUFFER", eglGetError());
    EGLint cxa[] = { EGL_CONTEXT_CLIENT_VERSION, want_version, EGL_NONE };
    EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, cxa);
    if (ctx == EGL_NO_CONTEXT) return fail("EGL_CONTEXT", eglGetError());
    if (!eglMakeCurrent(dpy, surf, surf, ctx)) return fail("EGL_MAKE_CURRENT", eglGetError());

    const char *ver = (const char *)glGetString(GL_VERSION);
    const char *ren = (const char *)glGetString(GL_RENDERER);
    printf("PROBE_CTX want=%d got=%s renderer=%s\n", want_version, ver ? ver : "?", ren ? ren : "?");
    drain_errors("startup");
    GLint max_tex = 0;
    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &max_tex);
    printf("PROBE_LIMITS max_texture=%d\n", max_tex);

    /* T1: 64x64 direct */
    GLuint t1 = 0;
    glGenTextures(1, &t1);
    glBindTexture(GL_TEXTURE_2D, t1);
    glCompressedTexImage2D(GL_TEXTURE_2D, 0, ASTC_6x6_FMT, 64, 64, 0, (GLsizei)sizeof(astc_6x6_data), astc_6x6_data);
    unsigned e1 = (unsigned)glGetError();
    printf("PROBE_T1 direct_64 err=0x%x bytes=%zu\n", e1, sizeof(astc_6x6_data));

    /* T2: 96x96 direct */
    GLuint t2 = 0;
    glGenTextures(1, &t2);
    glBindTexture(GL_TEXTURE_2D, t2);
    glCompressedTexImage2D(GL_TEXTURE_2D, 0, ASTC_6x6_FMT, 96, 96, 0, (GLsizei)sizeof(astc_6x6_data_96), astc_6x6_data_96);
    unsigned e2 = (unsigned)glGetError();
    printf("PROBE_T2 direct_96 err=0x%x bytes=%zu\n", e2, sizeof(astc_6x6_data_96));

    /* T3: ES3 storage path on 96x96 */
    GLuint t3 = 0;
    glGenTextures(1, &t3);
    glBindTexture(GL_TEXTURE_2D, t3);
    glTexStorage2D(GL_TEXTURE_2D, 1, ASTC_6x6_FMT, 96, 96);
    unsigned e3a = (unsigned)glGetError();
    unsigned e3b = 0;
    if (!e3a) {
        glCompressedTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 96, 96, ASTC_6x6_FMT, (GLsizei)sizeof(astc_6x6_data_96), astc_6x6_data_96);
        e3b = (unsigned)glGetError();
    }
    printf("PROBE_T3 storage_96 storage_err=0x%x subimage_err=0x%x\n", e3a, e3b);

    int ok = 1;
    if (!e1) ok &= (render_and_dump(t1, 64, 64, "astc_probe_out_64.ppm") == 0);
    if (!e2) ok &= (render_and_dump(t2, 96, 96, "astc_probe_out_96.ppm") == 0);
    printf("PROBE_RESULT ok=%d\n", ok);
    return ok ? 0 : 1;
}
