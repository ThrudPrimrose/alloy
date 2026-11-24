// softhiergen: strip-mined RVV loops over TCDM for the Spatz core (core 0), the spellings of Alloy's checked
// SoftHier rows (alloy/isa/softhier.toml): vsetvl at LMUL 8, unit-stride vle/vse, the tail as the last strip.
// Names: dsh_rvv_<op>_<suffix>, suffix f32, f16 or i32. Usable from C and C++.
#ifndef DSH_RVV_H
#define DSH_RVV_H

#include <riscv_vector.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef _Float16 dsh_f16;

// Every vector instruction stays inside a dsh_rvv_* function, called on the Spatz core only: inlined into a role-guarded
// caller, GCC may hoist vsetvl and the loads above the guard, onto cores without Spatz.
#define DSH_RVV_FN static inline __attribute__((noinline))

// Completes the Spatz core's vector stores before what follows (a barrier, a RedMulE trigger, an iDMA). RVV orders
// vector accesses with fence; GVSoC's Spatz model (gvsoc-core fence_exec) does not drain the VLSU on fence, but it
// stalls a scalar load of the Spatz core until every pending vector store has ended (Sequencer::load_store_handler).
static inline void dsh_vfence(void) { __asm__ volatile("fence\n\tlw zero, 0(sp)" ::: "memory"); }

// z = x OP y
#define DSH_RVV_VV(NAME, T, VT, S, B, OP)                                                           \
    DSH_RVV_FN void dsh_rvv_##NAME##_##S(T* z, const T* x, const T* y, size_t n) {               \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT a = __riscv_vle##B##_v_##S##m8(x + i, vl);                                           \
            VT b = __riscv_vle##B##_v_##S##m8(y + i, vl);                                           \
            __riscv_vse##B##_v_##S##m8(z + i, __riscv_##OP##_vv_##S##m8(a, b, vl), vl);             \
            i += vl;                                                                                \
        }                                                                                           \
    }

// z = x OP s, s one value (VS is vf for floats, vx for integers)
#define DSH_RVV_VS(NAME, T, VT, S, B, OP, VS)                                                       \
    DSH_RVV_FN void dsh_rvv_##NAME##_s_##S(T* z, const T* x, T s, size_t n) {                    \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT a = __riscv_vle##B##_v_##S##m8(x + i, vl);                                           \
            __riscv_vse##B##_v_##S##m8(z + i, __riscv_##OP##_##VS##_##S##m8(a, s, vl), vl);         \
            i += vl;                                                                                \
        }                                                                                           \
    }

// z = s OP x, for the operators that do not commute: s broadcast, then the vector-vector OP (GVSoC's Spatz has no
// vfrdiv and stops silently on it)
#define DSH_RVV_SV(NAME, T, VT, S, B, OP)                                                           \
    DSH_RVV_FN void dsh_rvv_##NAME##_r_##S(T* z, T s, const T* x, size_t n) {                    \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT a = __riscv_vle##B##_v_##S##m8(x + i, vl);                                           \
            VT b = __riscv_vfmv_v_f_##S##m8(s, vl);                                                 \
            __riscv_vse##B##_v_##S##m8(z + i, __riscv_##OP##_vv_##S##m8(b, a, vl), vl);             \
            i += vl;                                                                                \
        }                                                                                           \
    }

// d = a * b + c, one rounding (vfmacc: acc += a * b)
#define DSH_RVV_FMA(T, VT, S, B, MACC, VS)                                                              \
    DSH_RVV_FN void dsh_rvv_fma_##S(T* d, const T* a, const T* b, const T* c, size_t n) {        \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT va = __riscv_vle##B##_v_##S##m8(a + i, vl);                                          \
            VT vb = __riscv_vle##B##_v_##S##m8(b + i, vl);                                          \
            VT acc = __riscv_vle##B##_v_##S##m8(c + i, vl);                                         \
            __riscv_vse##B##_v_##S##m8(d + i, __riscv_##MACC##_vv_##S##m8(acc, va, vb, vl), vl);    \
            i += vl;                                                                                \
        }                                                                                           \
    }                                                                                               \
    /* d = s * b + c, s one value */                                                                \
    DSH_RVV_FN void dsh_rvv_fma_s_##S(T* d, T s, const T* b, const T* c, size_t n) {             \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT vb = __riscv_vle##B##_v_##S##m8(b + i, vl);                                          \
            VT acc = __riscv_vle##B##_v_##S##m8(c + i, vl);                                         \
            __riscv_vse##B##_v_##S##m8(d + i, __riscv_##MACC##_##VS##_##S##m8(acc, s, vb, vl), vl);     \
            i += vl;                                                                                \
        }                                                                                           \
    }

// y = x through vector registers
#define DSH_RVV_COPY(T, VT, S, B)                                                                   \
    DSH_RVV_FN void dsh_rvv_copy_##S(T* y, const T* x, size_t n) {                               \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT v = __riscv_vle##B##_v_##S##m8(x + i, vl);                                           \
            __riscv_vse##B##_v_##S##m8(y + i, v, vl);                                               \
            i += vl;                                                                                \
        }                                                                                           \
    }

// The reduction of x[0:n]: RED folds a strip into acc; sum starts from 0, max and min from x[0] (n >= 1)
#define DSH_RVV_RED(NAME, T, VT, V1, S, B, RED, MV_S, MV_F, INIT)                                   \
    DSH_RVV_FN T dsh_rvv_red##NAME##_##S(const T* x, size_t n) {                                 \
        V1 acc = __riscv_##MV_S##_##S##m1(INIT, 1);                                                 \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT v = __riscv_vle##B##_v_##S##m8(x + i, vl);                                           \
            acc = __riscv_##RED##_vs_##S##m8_##S##m1(v, acc, vl);                                   \
            i += vl;                                                                                \
        }                                                                                           \
        return __riscv_##MV_F##_##S##m1_##S(acc);                                                   \
    }

// z = OP x, one vector instruction (vfneg, vfabs, vfsqrt); not among Alloy's rows, checked by the gate's run
#define DSH_RVV_V(NAME, T, VT, S, B, OP)                                                            \
    DSH_RVV_FN void dsh_rvv_##NAME##_##S(T* z, const T* x, size_t n) {                           \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            VT a = __riscv_vle##B##_v_##S##m8(x + i, vl);                                           \
            __riscv_vse##B##_v_##S##m8(z + i, __riscv_##OP##_v_##S##m8(a, vl), vl);                 \
            i += vl;                                                                                \
        }                                                                                           \
    }

#define DSH_RVV_FLOAT(T, S, B)                                                                      \
    DSH_RVV_VV(add, T, vfloat##B##m8_t, S, B, vfadd)                                                \
    DSH_RVV_VV(sub, T, vfloat##B##m8_t, S, B, vfsub)                                                \
    DSH_RVV_VV(mul, T, vfloat##B##m8_t, S, B, vfmul)                                                \
    DSH_RVV_VV(div, T, vfloat##B##m8_t, S, B, vfdiv)                                                \
    DSH_RVV_VV(max, T, vfloat##B##m8_t, S, B, vfmax)                                                \
    DSH_RVV_VV(min, T, vfloat##B##m8_t, S, B, vfmin)                                                \
    DSH_RVV_VS(add, T, vfloat##B##m8_t, S, B, vfadd, vf)                                            \
    DSH_RVV_VS(sub, T, vfloat##B##m8_t, S, B, vfsub, vf)                                            \
    DSH_RVV_VS(mul, T, vfloat##B##m8_t, S, B, vfmul, vf)                                            \
    DSH_RVV_VS(div, T, vfloat##B##m8_t, S, B, vfdiv, vf)                                            \
    DSH_RVV_VS(max, T, vfloat##B##m8_t, S, B, vfmax, vf)                                            \
    DSH_RVV_VS(min, T, vfloat##B##m8_t, S, B, vfmin, vf)                                            \
    DSH_RVV_SV(sub, T, vfloat##B##m8_t, S, B, vfsub)                                                   \
    DSH_RVV_SV(div, T, vfloat##B##m8_t, S, B, vfdiv)                                                   \
    DSH_RVV_V(neg, T, vfloat##B##m8_t, S, B, vfneg)                                                 \
    DSH_RVV_V(abs, T, vfloat##B##m8_t, S, B, vfabs)                                                 \
    DSH_RVV_V(sqrt, T, vfloat##B##m8_t, S, B, vfsqrt)                                               \
    DSH_RVV_FMA(T, vfloat##B##m8_t, S, B, vfmacc, vf)                                                   \
    DSH_RVV_RED(sum, T, vfloat##B##m8_t, vfloat##B##m1_t, S, B, vfredusum, vfmv_s_f, vfmv_f_s, (T)0) \
    DSH_RVV_RED(max, T, vfloat##B##m8_t, vfloat##B##m1_t, S, B, vfredmax, vfmv_s_f, vfmv_f_s, x[0])  \
    DSH_RVV_RED(min, T, vfloat##B##m8_t, vfloat##B##m1_t, S, B, vfredmin, vfmv_s_f, vfmv_f_s, x[0])

DSH_RVV_FLOAT(float, f32, 32)
DSH_RVV_FLOAT(dsh_f16, f16, 16)

DSH_RVV_VV(add, int32_t, vint32m8_t, i32, 32, vadd)
DSH_RVV_VV(sub, int32_t, vint32m8_t, i32, 32, vsub)
DSH_RVV_VV(mul, int32_t, vint32m8_t, i32, 32, vmul)
DSH_RVV_VV(max, int32_t, vint32m8_t, i32, 32, vmax)
DSH_RVV_VV(min, int32_t, vint32m8_t, i32, 32, vmin)
DSH_RVV_VS(add, int32_t, vint32m8_t, i32, 32, vadd, vx)
DSH_RVV_VS(sub, int32_t, vint32m8_t, i32, 32, vsub, vx)
DSH_RVV_VS(mul, int32_t, vint32m8_t, i32, 32, vmul, vx)
DSH_RVV_VS(max, int32_t, vint32m8_t, i32, 32, vmax, vx)
DSH_RVV_VS(min, int32_t, vint32m8_t, i32, 32, vmin, vx)
DSH_RVV_FMA(int32_t, vint32m8_t, i32, 32, vmacc, vx)
DSH_RVV_RED(sum, int32_t, vint32m8_t, vint32m1_t, i32, 32, vredsum, vmv_s_x, vmv_x_s, 0)
DSH_RVV_RED(max, int32_t, vint32m8_t, vint32m1_t, i32, 32, vredmax, vmv_s_x, vmv_x_s, x[0])
DSH_RVV_RED(min, int32_t, vint32m8_t, vint32m1_t, i32, 32, vredmin, vmv_s_x, vmv_x_s, x[0])
DSH_RVV_COPY(uint8_t, vuint8m8_t, u8, 8)

// x[0:n] = s
#define DSH_RVV_FILL(T, VT, S, B, MV, VS)                                                           \
    DSH_RVV_FN void dsh_rvv_fill_##S(T* x, T s, size_t n) {                                      \
        for (size_t i = 0; i < n;) {                                                                \
            size_t vl = __riscv_vsetvl_e##B##m8(n - i);                                             \
            __riscv_vse##B##_v_##S##m8(x + i, __riscv_##MV##_##VS##_##S##m8(s, vl), vl);            \
            i += vl;                                                                                \
        }                                                                                           \
    }
DSH_RVV_FILL(float, vfloat32m8_t, f32, 32, vfmv_v, f)
DSH_RVV_FILL(dsh_f16, vfloat16m8_t, f16, 16, vfmv_v, f)
DSH_RVV_FILL(int32_t, vint32m8_t, i32, 32, vmv_v, x)


// Comparisons and selects are scalar loops on the Spatz core: GVSoC's Spatz model stops silently on the mask
// instructions (vmflt/vmslt into a mask, vmsne, vmerge; probed 2026-11-24, ault job 923527), as on vfrdiv.
// shortcut: no vector compare until the model takes masks; switch back to vm*/vmerge once a planted row checks them.
// A bool tile holds one byte per lane, 0 or 1.
#define DSH_RVV_CMP(NAME, T, S, OP)                                                                 \
    DSH_RVV_FN void dsh_rvv_##NAME##_##S(bool* z, const T* x, const T* y, size_t n) {            \
        for (size_t i = 0; i < n; ++i) z[i] = x[i] OP y[i];                                         \
    }                                                                                               \
    DSH_RVV_FN void dsh_rvv_##NAME##_s_##S(bool* z, const T* x, T s, size_t n) {                 \
        for (size_t i = 0; i < n; ++i) z[i] = x[i] OP s;                                            \
    }
// z = c ? t : e per lane, c a bool tile; _ts: t one value, _es: e one value
#define DSH_RVV_SELECT(T, S)                                                                        \
    DSH_RVV_FN void dsh_rvv_select_##S(T* z, const bool* c, const T* t, const T* e, size_t n) {  \
        for (size_t i = 0; i < n; ++i) z[i] = c[i] ? t[i] : e[i];                                   \
    }                                                                                               \
    DSH_RVV_FN void dsh_rvv_select_ts_##S(T* z, const bool* c, T t, const T* e, size_t n) {      \
        for (size_t i = 0; i < n; ++i) z[i] = c[i] ? t : e[i];                                      \
    }                                                                                               \
    DSH_RVV_FN void dsh_rvv_select_es_##S(T* z, const bool* c, const T* t, T e, size_t n) {      \
        for (size_t i = 0; i < n; ++i) z[i] = c[i] ? t[i] : e;                                      \
    }
#define DSH_RVV_COMPARES(T, S)                                                                      \
    DSH_RVV_CMP(lt, T, S, <)                                                                        \
    DSH_RVV_CMP(le, T, S, <=)                                                                       \
    DSH_RVV_CMP(gt, T, S, >)                                                                        \
    DSH_RVV_CMP(ge, T, S, >=)                                                                       \
    DSH_RVV_CMP(eq, T, S, ==)                                                                       \
    DSH_RVV_CMP(ne, T, S, !=)                                                                       \
    DSH_RVV_SELECT(T, S)

DSH_RVV_COMPARES(float, f32)
DSH_RVV_COMPARES(dsh_f16, f16)
DSH_RVV_COMPARES(int32_t, i32)

#endif  // DSH_RVV_H
