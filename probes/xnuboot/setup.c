/* SPDX-License-Identifier: MIT */
/* xnuboot_setup and xnuboot_save: the monitor-side state set up before entry.
 * Part of probes/xnuboot.c's translation unit, included in order; not compiled on its own. */

static inline void fb_stripe(uint32_t color, uint32_t width_fraction)
{
    volatile uint32_t *fb = (volatile uint32_t *)0xe4800000ULL;
    uint32_t limit = (2880 * width_fraction) / 10;
    if (limit > 2880) limit = 2880;
    for (uint32_t y = 0; y < 16; y++) {
        for (uint32_t x = 0; x < limit; x++) {
            fb[y * 2880 + x] = color;
        }
    }
    __asm__ volatile("dsb sy" ::: "memory");
}

int xnuboot_setup(uint64_t work, uint64_t size, uint64_t params, uint64_t out,
                  const struct secondary_config *host_cpus);
static inline void fast_zero_context(void *ptr, uint64_t bytes)
{
    uint64_t *p = (uint64_t *)ptr;
    uint64_t count = (bytes + 63) / 64;
    __asm__ volatile(
        "1:\n"
        "stp xzr, xzr, [%0], #16\n"
        "stp xzr, xzr, [%0], #16\n"
        "stp xzr, xzr, [%0], #16\n"
        "stp xzr, xzr, [%0], #16\n"
        "subs %1, %1, #1\n"
        "b.ne 1b\n"
        : "+r"(p), "+r"(count)
        :
        : "memory", "cc"
    );
}

int xnuboot_setup(uint64_t work, uint64_t size, uint64_t params, uint64_t out,
                  const struct secondary_config *host_cpus)
{
    fb_con_init();
    fb_stripe(0x00ffff, 2);
    fb_con_print("========================================================\n");
    fb_con_print(" SNAPINTOSH XNUBOOT EL2 HYPERVISOR MONITOR ACTIVATED\n");
    fb_con_print(" TARGET: ASUS VIVOBOOK S 15 (QUALCOMM ORYON V1 X1E-78)\n");
    fb_con_print(" GUEST:  MACOS 27 SEQUOIA (BUILD 26A428 / T8140)\n");
    fb_con_print("========================================================\n");
    fb_con_print("[+] INITIALIZING CONTEXT AND VCPUS...\n");
    struct context *c = (struct context *)work;
    fb_con_print_hex("    WORK PA:   ", work);
    fb_con_print_hex("    WORK SIZE: ", size);
    fb_con_print_hex("    PARAMS PA: ", params);

    fast_zero_context(c, sizeof(*c));
    fb_con_print("[+] FULL CONTEXT ZEROED (10 MB CLEAN)\n");

#if SNAP_ROOT_CACHE_WIDE
    if (size < sizeof(*c) + 4096 + ROOT_EXT_PAGES * 4096) {
        fb_con_print("[-] SETUP ERR: SIZE TOO SMALL FOR ROOT_EXT\n");
        return 1;
    }
    c->root_ext = (struct root_ext *)((work + sizeof(*c) + 0xfff) & ~0xfffUL);
    for (uint64_t n = 0; n < ROOT_EXT_PAGES * 4096 / 8; n++) ((volatile uint64_t *)c->root_ext)[n] = 0;
#endif

#if SNAP_TXM_ASPACE_WIDE
    if ((work & 0xfff) || size < TXM_EXT_OFFSET + TXM_EXT_PAGES * 4096 + 4096) {
        fb_con_print("[-] SETUP ERR: TXM_EXT_OFFSET OUT OF BOUNDS\n");
        return 1;
    }
    for (uint64_t n = 0; n < TXM_EXT_PAGES * 4096 / 8; n++) ((volatile uint64_t *)TXM_REG(c))[n] = 0;
#endif

    c->params = (const struct params *)params;
    c->writer_breakpoints_enabled=SNAP_NATIVE_WRITER_BREAKPOINTS;
    c->host_cpus=host_cpus;
    for (unsigned n = 0; n < GUEST_CPU_COUNT; n++) {
        c->vcpus[n].context = c;
        c->vcpus[n].slot = n;
        c->vcpus[n].vmpidr = 0x80000000UL | (n < 4 ? n : 0x100+n-4);
        sprr_root_reset(&c->user_roots.sprr[n],0);
        if(!sptm_root_note_loaded(&c->user_roots,c->root_loaded,n)) {
            fb_con_print("[-] SETUP ERR: SPTM_ROOT_NOTE_LOADED FAILED\n");
            return 1;
        }
        pauth_user_init(&c->user_pauth[n]);
        c->vcpus[n].guest_apga_lo=c->user_pauth[n].key[PAUTH_GA].lo;
        c->vcpus[n].guest_apga_hi=c->user_pauth[n].key[PAUTH_GA].hi;
    }
    fb_con_print("[+] VCPUS 0-5 INITIALIZED\n");

    c->vcpus[0].vmpidr = c->params->vmpidr;
    c->vcpus[0].vncr_va = c->params->vncr_va;
    __asm__ volatile("msr tpidr_el2, %0; isb" :: "r"(&c->vcpus[0]) : "memory");
    fb_con_print("[+] TPIDR_EL2 SET TO VCPU 0\n");

    c->skip_undef = c->params->skip_undef;
    vcpu_of(c)->out_ptr = out;
    c->cpus.registered = 1;
    c->next_table = (work + sizeof(*c) + 0xfff) & ~0xfffUL;
    c->work_start = work;
    c->work_base = c->next_table;
#if SNAP_ROOT_CACHE_WIDE
    c->next_table += ROOT_EXT_PAGES * 4096;
#endif
#if SNAP_TXM_ASPACE_WIDE
    if (c->next_table != (uint64_t)TXM_REG(c)) {
        fb_con_print("[-] SETUP ERR: NEXT_TABLE != TXM_REG\n");
        return 1;
    }
    c->next_table += TXM_EXT_PAGES * 4096;
#endif
#if SNAP_USER_HW_WALK
    if (c->next_table + HW_WALK_PAGES * 4096 > work + size) {
        fb_con_print("[-] SETUP ERR: HW_WALK_PAGES OUT OF BOUNDS\n");
        return 1;
    }
    c->hw_walk = (struct hw_walk_state *)c->next_table;
    for (uint64_t n = 0; n < HW_WALK_PAGES * 4096 / 8; n++) ((volatile uint64_t *)c->hw_walk)[n] = 0;
    __asm__ volatile("" ::: "memory");
    for (unsigned n = 0; n < HW_WALK_ROOTS; n++) c->hw_walk->roots[n].index = n;
    c->next_table += HW_WALK_PAGES * 4096;
#endif
    c->work_end = work + size;
    if(c->params->txm_native.image) {
        const struct txm_native_params *n=&c->params->txm_native;
        if(n->image!=0xb0600000 || n->size!=TXM_NATIVE_BYTES ||
           size<TXM_NATIVE_BYTES || n->work!=work+size-TXM_NATIVE_BYTES ||
           (n->work&0x3fff) || !n->tree_size || n->tree_size>0x100000) {
            fb_con_print("[-] SETUP ERR: TXM_NATIVE_PARAMS INVALID\n");
            return 1;
        }
        c->work_end=n->work;
    } else if(c->params->txm_native.work || c->params->txm_native.size || c->params->txm_native.tree_size) {
        fb_con_print("[-] SETUP ERR: UNEXPECTED TXM_NATIVE PARAMS\n");
        return 1;
    }
#if SNAP_S2_FAULT_RETRY
    if (c->next_table + S2_RETRY_PAGES * 4096 > c->work_end) {
        fb_con_print("[-] SETUP ERR: S2_RETRY OUT OF BOUNDS\n");
        return 1;
    }
    c->s2_retry = (struct s2_retry_state *)c->next_table;
    for (uint64_t n = 0; n < S2_RETRY_PAGES * 4096 / 8; n++) ((volatile uint64_t *)c->s2_retry)[n] = 0;
    __asm__ volatile("" ::: "memory");
    c->next_table += S2_RETRY_PAGES * 4096;
#endif
#if SNAP_GUEST_NET
    if (c->next_table + GUEST_NET_STATE_PAGES * 4096 > c->work_end) {
        fb_con_print("[-] SETUP ERR: GUEST_NET OUT OF BOUNDS\n");
        return 1;
    }
    c->guest_net = (struct guest_net_state *)c->next_table;
    for (uint64_t n = 0; n < GUEST_NET_STATE_PAGES * 4096 / 8; n++) ((volatile uint64_t *)c->guest_net)[n] = 0;
    __asm__ volatile("" ::: "memory");
    c->next_table += GUEST_NET_STATE_PAGES * 4096;
#endif
#if SNAP_EDP_BACKLIGHT
    if (c->next_table + 4096 > c->work_end) {
        fb_con_print("[-] SETUP ERR: EDP_BACKLIGHT OUT OF BOUNDS\n");
        return 1;
    }
    c->edp_backlight = (struct edp_backlight_state *)c->next_table;
    for (uint64_t n = 0; n < 4096 / 8; n++) ((volatile uint64_t *)c->edp_backlight)[n] = 0;
    __asm__ volatile("" ::: "memory");
    c->next_table += 4096;
#endif
    if(c->params->early_stop.flags & EARLY_STOP_F_THERMAL) {
        if(c->next_table>c->work_end || c->work_end-c->next_table<4096) {
            fb_con_print("[-] SETUP ERR: THERMAL OUT OF BOUNDS\n");
            return 1;
        }
        c->thermal=(struct a16_thermal_state *)c->next_table;
        for(unsigned n=0;n<4096/8;n++)((volatile uint64_t *)c->thermal)[n]=0;
        __asm__ volatile("" ::: "memory");
        c->next_table+=4096;
    }
    if(c->work_end<c->work_base || (c->work_end-c->work_base)/4096>TABLE_POOL_MAX) {
        fb_con_print("[-] SETUP ERR: TABLE POOL MAX EXCEEDED\n");
        fb_con_print_hex("    WORK_BASE: ", c->work_base);
        fb_con_print_hex("    WORK_END:  ", c->work_end);
        fb_con_print_hex("    PAGES:     ", (c->work_end - c->work_base) / 4096);
        fb_con_print_hex("    MAX_PAGES: ", TABLE_POOL_MAX);
        return 1;
    }
    c->table_pool.head=TABLE_POOL_MAX;
    c->table_memo.base=c->work_base;
    c->table_memo.pages=(c->work_end-c->work_base)/4096;
    for(unsigned i=0;i<SPTM_ROOT_CACHE;i++) {
        UOWNERS(c)[i].context=c;UOWNERS(c)[i].owner=i+1;
    }
    fb_stripe(0x0088ff, 3);
    fb_con_print("[+] XNUBOOT SETUP COMPLETE\n");
    return 0;
}

void xnuboot_save(uint64_t vbar, uint64_t hcr, uint64_t tpidr,
                  uint64_t sctlr, uint64_t tcr, uint64_t daif);
void xnuboot_save(uint64_t vbar, uint64_t hcr, uint64_t tpidr,
                  uint64_t sctlr, uint64_t tcr, uint64_t daif)
{
    struct context *c = context_of();
    vcpu_of(c)->save_vbar = vbar;
    vcpu_of(c)->save_hcr = hcr;
    vcpu_of(c)->save_tpidr = tpidr;
    vcpu_of(c)->save_sctlr = sctlr;
    vcpu_of(c)->save_tcr = tcr;
    vcpu_of(c)->save_daif = daif;
}
