/* SPDX-License-Identifier: MIT */
/* Fast on-screen framebuffer console and diagnostics overlay for Snapintosh.
 * Dynamic framebuffer geometry and base detection (supports ASUS OLED 2880x1620 and QEMU GOP).
 * Part of probes/xnuboot translation unit. ZERO BSS / ZERO DATA. */

#ifndef FB_CONSOLE_H
#define FB_CONSOLE_H

#include <stdint.h>

struct fb_info {
    uint64_t base;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
};

static inline int fb_get_info(struct fb_info *info)
{
    uint64_t tpidr = 0;
    __asm__ volatile("mrs %0, tpidr_el2" : "=r"(tpidr));
    if (!tpidr) {
        return 0;
    }
    struct vcpu *v = (struct vcpu *)tpidr;
    if (!v || !v->context || !v->context->params) {
        return 0;
    }
    const struct params *p = v->context->params;
    if (!p->fb_pa || !p->fb_span) {
        return 0;
    }
    info->base = p->fb_pa;
    if (p->fb_span >= 0x1000000ULL) {
        info->width = 2880;
        info->height = 1620;
        info->stride = 2880;
    } else if (p->fb_span <= 0x380000ULL) {
        info->width = 800;
        info->height = 600;
        info->stride = 800;
    } else {
        info->width = 1024;
        info->height = 768;
        info->stride = 1024;
    }
    return 1;
}

static inline volatile uint32_t *fb_get_cursor(const struct fb_info *info)
{
    return (volatile uint32_t *)(info->base + (info->stride * info->height - 2) * 4);
}

static const char fb_alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-./=?()_ []<>,+*#$!\n\r";
static const uint8_t fb_glyphs[][7] = {
    {14,17,17,31,17,17,17}, /* A */
    {30,17,17,30,17,17,30}, /* B */
    {14,17,16,16,16,17,14}, /* C */
    {30,17,17,17,17,17,30}, /* D */
    {31,16,16,30,16,16,31}, /* E */
    {31,16,16,30,16,16,16}, /* F */
    {14,17,16,23,17,17,15}, /* G */
    {17,17,17,31,17,17,17}, /* H */
    {14,4,4,4,4,4,14},      /* I */
    {7,2,2,2,2,18,12},     /* J */
    {17,18,20,24,20,18,17}, /* K */
    {16,16,16,16,16,16,31}, /* L */
    {17,27,21,21,17,17,17}, /* M */
    {17,25,21,19,17,17,17}, /* N */
    {14,17,17,17,17,17,14}, /* O */
    {30,17,17,30,16,16,16}, /* P */
    {14,17,17,17,21,18,13}, /* Q */
    {30,17,17,30,20,18,17}, /* R */
    {15,16,16,14,1,1,30},   /* S */
    {31,4,4,4,4,4,4},       /* T */
    {17,17,17,17,17,17,14}, /* U */
    {17,17,17,17,17,10,4},  /* V */
    {17,17,17,21,21,21,10}, /* W */
    {17,17,10,4,10,17,17},  /* X */
    {17,17,10,4,4,4,4},     /* Y */
    {31,1,2,4,8,16,31},     /* Z */
    {14,17,19,21,25,17,14}, /* 0 */
    {4,12,4,4,4,4,14},      /* 1 */
    {14,17,1,2,4,8,31},     /* 2 */
    {30,1,1,14,1,1,30},     /* 3 */
    {2,6,10,18,31,2,2},     /* 4 */
    {31,16,16,30,1,1,30},   /* 5 */
    {14,16,16,30,17,17,14}, /* 6 */
    {31,1,2,4,8,8,8},       /* 7 */
    {14,17,17,14,17,17,14}, /* 8 */
    {14,17,17,15,1,1,14},   /* 9 */
    {0,4,4,0,4,4,0},        /* : */
    {0,0,0,31,0,0,0},       /* - */
    {0,0,0,0,0,4,4},        /* . */
    {1,2,2,4,8,8,16},       /* / */
    {0,0,31,0,31,0,0},      /* = */
    {14,17,1,2,4,0,4},      /* ? */
    {2,4,8,8,8,4,2},        /* ( */
    {8,4,2,2,2,4,8},        /* ) */
    {0,0,0,0,0,0,31},       /* _ */
    {0,0,0,0,0,0,0},        /* ' ' */
    {14,8,8,8,8,8,14},      /* [ */
    {14,2,2,2,2,2,14},      /* ] */
    {2,4,8,16,8,4,2},       /* < */
    {8,4,2,1,2,4,8},        /* > */
    {0,0,0,0,4,4,8},        /* , */
    {0,4,4,31,4,4,0},       /* + */
    {0,21,14,31,14,21,0},   /* * */
    {10,31,10,10,31,10,0},  /* # */
    {4,15,20,14,5,30,4},    /* $ */
    {4,4,4,4,4,0,4}         /* ! */
};

static inline void fb_clear_rect(uint32_t x0, uint32_t y0, uint32_t w, uint32_t h, uint32_t color)
{
    struct fb_info info;
    if (!fb_get_info(&info)) return;
    volatile uint32_t *fb = (volatile uint32_t *)info.base;
    for (uint32_t y = y0; y < y0 + h && y < info.height; y++) {
        for (uint32_t x = x0; x < x0 + w && x < info.width; x++) {
            fb[y * info.stride + x] = color;
        }
    }
    __asm__ volatile("dsb sy" ::: "memory");
}

static inline void fb_con_put(uint8_t c)
{
    struct fb_info info;
    if (!fb_get_info(&info)) return;
    volatile uint32_t *fb = (volatile uint32_t *)info.base;
    volatile uint32_t *cursor = fb_get_cursor(&info);
    uint32_t col = cursor[0];
    uint32_t row = cursor[1];

    uint32_t max_rows = (info.height > 100) ? (info.height - 40) / 18 : 30;

    if (c == '\r') {
        cursor[0] = 0;
        return;
    }
    if (c == '\n') {
        cursor[0] = 0;
        row++;
        if (row >= max_rows) {
            row = 0;
            fb_clear_rect(0, 32, info.width, info.height - 32, 0x00050810);
        }
        cursor[1] = row;
        return;
    }
    if (c >= 'a' && c <= 'z') c -= 32;

    uint32_t scale = (info.width > 1200) ? 2 : 1;
    uint32_t char_w = 6 * scale;
    uint32_t char_h = 9 * scale;

    if ((col + 1) * char_w >= (info.width - 20)) {
        col = 0;
        row++;
        if (row >= max_rows) {
            row = 0;
            fb_clear_rect(0, 32, info.width, info.height - 32, 0x00050810);
        }
    }

    uint32_t px0 = 16 + col * char_w;
    uint32_t py0 = 36 + row * char_h;

    const uint8_t *glyph = 0;
    for (unsigned g = 0; g < sizeof(fb_glyphs) / sizeof(fb_glyphs[0]); g++) {
        if (fb_alphabet[g] == c) {
            glyph = fb_glyphs[g];
            break;
        }
    }

    /* Clear character cell */
    for (uint32_t j = 0; j < char_h && py0 + j < info.height; j++) {
        for (uint32_t i = 0; i < char_w && px0 + i < info.width; i++) {
            fb[(py0 + j) * info.stride + (px0 + i)] = 0x00050810;
        }
    }

    if (glyph) {
        for (uint32_t j = 0; j < 7; j++) {
            for (uint32_t i = 0; i < 5; i++) {
                if (glyph[j] & (1u << (4 - i))) {
                    for (uint32_t sy = 0; sy < scale; sy++) {
                        for (uint32_t sx = 0; sx < scale; sx++) {
                            uint32_t x = px0 + i * scale + sx;
                            uint32_t y = py0 + j * scale + sy;
                            if (x < info.width && y < info.height) {
                                fb[y * info.stride + x] = 0x00e6edf3;
                            }
                        }
                    }
                }
            }
        }
    }

    cursor[0] = col + 1;
    cursor[1] = row;
    __asm__ volatile("dsb sy" ::: "memory");
}

static inline void fb_con_print(const char *s)
{
    while (*s) {
        fb_con_put((uint8_t)*s++);
    }
}

static inline void fb_con_print_hex(const char *prefix, uint64_t val)
{
    fb_con_print(prefix);
    fb_con_print("0X");
    for (int i = 15; i >= 0; i--) {
        uint8_t nibble = (val >> (i * 4)) & 0xf;
        char ch = nibble < 10 ? '0' + nibble : 'A' + (nibble - 10);
        fb_con_put(ch);
    }
    fb_con_print("\n");
}

static const uint8_t apple_logo_bits[360] = {
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf0, 0x00, 0x00,
    0x00, 0x00, 0x00, 0xf8, 0x00, 0x00, 0x00, 0x00, 0x00, 0xfc, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x7e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x3f, 0x80, 0x00, 0x00, 0x00, 0x00, 0x1f, 0xc0, 0x00,
    0x00, 0x00, 0x00, 0x0f, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x0f, 0xc0, 0x00,
    0x00, 0x00, 0x00, 0x07, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x03, 0xe0, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x78, 0x0e, 0x00, 0x00,
    0x00, 0x01, 0xf8, 0x0f, 0x80, 0x00, 0x00, 0x03, 0xfc, 0x1f, 0xc0, 0x00,
    0x00, 0x0f, 0xfe, 0x3f, 0xf0, 0x00, 0x00, 0x1f, 0xff, 0x7f, 0xf8, 0x00,
    0x00, 0x3f, 0xff, 0xff, 0xfc, 0x00, 0x00, 0x7f, 0xff, 0xff, 0xfe, 0x00,
    0x00, 0x7f, 0xff, 0xff, 0xfe, 0x00, 0x00, 0xff, 0xff, 0xff, 0xf0, 0x00,
    0x01, 0xff, 0xff, 0xff, 0xc0, 0x00, 0x01, 0xff, 0xff, 0xff, 0x80, 0x00,
    0x01, 0xff, 0xff, 0xff, 0x00, 0x00, 0x03, 0xff, 0xff, 0xff, 0x00, 0x00,
    0x03, 0xff, 0xff, 0xfe, 0x00, 0x00, 0x03, 0xff, 0xff, 0xfe, 0x00, 0x00,
    0x07, 0xff, 0xff, 0xfe, 0x00, 0x00, 0x07, 0xff, 0xff, 0xfe, 0x00, 0x00,
    0x07, 0xff, 0xff, 0xfe, 0x00, 0x00, 0x07, 0xff, 0xff, 0xff, 0x00, 0x00,
    0x07, 0xff, 0xff, 0xff, 0x00, 0x00, 0x07, 0xff, 0xff, 0xff, 0x80, 0x00,
    0x07, 0xff, 0xff, 0xff, 0xc0, 0x00, 0x07, 0xff, 0xff, 0xff, 0xf0, 0x60,
    0x07, 0xff, 0xff, 0xff, 0xff, 0xe0, 0x03, 0xff, 0xff, 0xff, 0xff, 0xc0,
    0x03, 0xff, 0xff, 0xff, 0xff, 0xc0, 0x03, 0xff, 0xff, 0xff, 0xff, 0xc0,
    0x01, 0xff, 0xff, 0xff, 0xff, 0x80, 0x01, 0xff, 0xff, 0xff, 0xff, 0x80,
    0x01, 0xff, 0xff, 0xff, 0xff, 0x80, 0x00, 0xff, 0xff, 0xff, 0xff, 0x00,
    0x00, 0x7f, 0xff, 0xff, 0xfe, 0x00, 0x00, 0x7f, 0xfe, 0x3f, 0xfe, 0x00,
    0x00, 0x3f, 0xfc, 0x1f, 0xfc, 0x00, 0x00, 0x1f, 0xf8, 0x0f, 0xf8, 0x00,
    0x00, 0x0f, 0xf0, 0x07, 0xf0, 0x00, 0x00, 0x03, 0xe0, 0x03, 0xc0, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static inline void fb_draw_apple_boot_screen(const struct fb_info *info)
{
    fb_clear_rect(0, 0, info->width, info->height, 0x00000000);
    uint32_t x0 = (info->width > 48) ? (info->width - 48) / 2 : 0;
    uint32_t y0 = (info->height > 60) ? (info->height - 60) / 2 - 25 : 0;

    for (uint32_t y = 0; y < 60; y++) {
        for (uint32_t b = 0; b < 6; b++) {
            uint8_t byte = apple_logo_bits[y * 6 + b];
            if (!byte) continue;
            for (uint32_t bit = 0; bit < 8; bit++) {
                if (byte & (1u << (7 - bit))) {
                    uint32_t px = x0 + b * 8 + bit;
                    uint32_t py = y0 + y;
                    if (px < info->width && py < info->height) {
                        volatile uint32_t *p = (volatile uint32_t *)(info->base + (py * info->stride + px) * 4);
                        *p = 0x00FFFFFF;
                    }
                }
            }
        }
    }

    uint32_t bar_w = 180;
    uint32_t bar_h = 5;
    uint32_t bx0 = (info->width > bar_w) ? (info->width - bar_w) / 2 : 0;
    uint32_t by0 = y0 + 60 + 35;
    fb_clear_rect(bx0, by0, bar_w, bar_h, 0x00333333);
    fb_clear_rect(bx0, by0, (bar_w * 45) / 100, bar_h, 0x00FFFFFF);
    __asm__ volatile("dsb sy" ::: "memory");
}

static inline void fb_con_init(void)
{
    struct fb_info info;
    if (!fb_get_info(&info)) return;
    fb_draw_apple_boot_screen(&info);
    volatile uint32_t *cursor = fb_get_cursor(&info);
    cursor[0] = 0;
    cursor[1] = 0;
}

static inline void fb_con_print_panic(const char *msg, uint64_t pc, uint64_t esr, uint64_t far)
{
    struct fb_info info;
    if (!fb_get_info(&info)) return;
    fb_clear_rect(0, 0, info.width, 200, 0x00880000);
    volatile uint32_t *cursor = fb_get_cursor(&info);
    cursor[0] = 0;
    cursor[1] = 0;
    fb_con_print("\n*** [XNUBOOT EL2 PANIC / HALT] ***\n");
    fb_con_print(msg);
    fb_con_print("\n");
    fb_con_print_hex("PC:  ", pc);
    fb_con_print_hex("ESR: ", esr);
    fb_con_print_hex("FAR: ", far);
    __asm__ volatile("dsb sy" ::: "memory");
}

#endif /* FB_CONSOLE_H */
