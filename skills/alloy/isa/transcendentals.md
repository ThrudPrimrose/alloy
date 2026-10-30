# Transcendentals — polynomial tiers with measured ULP (generated, do not edit)

ULP at function scale: max |approx − ref| / spacing(max(|ref|, 1.0)) against double-precision libm on dense grids; the reference's own 0.5 ulp is the floor. Recipes are Horner schemes in abstract-op steps (`fma`/`mul` with inline coefficients) — copyable implementations.

| tier | op | domain | error (ulp) | error (abs) |
|---|---|---|---|---|
| `sin-taylor7` | sin | |x| <= pi/2 after Cody-Waite reduction | 7.066e+11 | 0.000157 |
| `sin-taylor9` | sin | |x| <= pi/2 after Cody-Waite reduction | 1.595e+10 | 3.54e-06 |
| `sin-taylor11` | sin | |x| <= pi/2 after Cody-Waite reduction | 2.534e+08 | 5.63e-08 |
| `sin-quad-cheb9` | sin | |x| <= pi/4 after quadrant (mod pi/2) reduction | 3.101e+04 | 6.89e-12 |
| `sin-quad-cheb13` | sin | |x| <= pi/4 after quadrant (mod pi/2) reduction | 8.5 | 1.89e-15 |
| `cos-taylor6` | cos | |x| <= pi/2 after Cody-Waite reduction | 4.029e+12 | 0.000895 |
| `cos-taylor8` | cos | |x| <= pi/2 after Cody-Waite reduction | 1.114e+11 | 2.47e-05 |
| `cos-taylor10` | cos | |x| <= pi/2 after Cody-Waite reduction | 2.093e+09 | 4.65e-07 |
| `cos-quad-cheb8` | cos | |x| <= pi/4 after quadrant (mod pi/2) reduction | 4.343e+05 | 9.64e-11 |
| `cos-quad-cheb12` | cos | |x| <= pi/4 after quadrant (mod pi/2) reduction | 16 | 3.55e-15 |
| `exp-taylor5` | exp | |x| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 1.14e+10 | 2.53e-06 |
| `exp-taylor7` | exp | |x| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 2.418e+07 | 5.37e-09 |
| `exp-taylor9` | exp | |x| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 3.203e+04 | 7.11e-12 |
| `exp-cheb7` | exp | |x| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 4.736e+05 | 1.05e-10 |
| `exp-cheb9` | exp | |x| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 221 | 4.91e-14 |
| `exp-cheb11` | exp | |x| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 67 | 1.49e-14 |

## Recipes

### sin-taylor7

```
t = mul(x, x)
p = fma(-0.0001984126984126984, t, 0.008333333333333333)
p = fma(p, t, -0.16666666666666666)
s = fma(mul(x, t), p, x)
```

plain Taylor: cheap, inaccurate; the ladder shows why libraries use minimax

### sin-taylor9

```
t = mul(x, x)
p = fma(2.7557319223985893e-06, t, -0.0001984126984126984)
p = fma(p, t, 0.008333333333333333)
p = fma(p, t, -0.16666666666666666)
s = fma(mul(x, t), p, x)
```

plain Taylor: cheap, inaccurate; the ladder shows why libraries use minimax

### sin-taylor11

```
t = mul(x, x)
p = fma(-2.505210838544172e-08, t, 2.7557319223985893e-06)
p = fma(p, t, -0.0001984126984126984)
p = fma(p, t, 0.008333333333333333)
p = fma(p, t, -0.16666666666666666)
s = fma(mul(x, t), p, x)
```

plain Taylor: cheap, inaccurate; the ladder shows why libraries use minimax

### sin-quad-cheb9

```
t = mul(x, x)
p = fma(2.7173474601211545e-06, t, -0.00019839169723550524)
p = fma(p, t, 0.008333328480625443)
p = fma(p, t, -0.16666666623931767)
p = fma(p, t, 0.999999999991219)
s = mul(x, p)
```

Chebyshev-fit near-minimax on the quadrant; SLEEF u10 adds double-double reduction for ~1 ulp total

### sin-quad-cheb13

```
t = mul(x, x)
p = fma(1.779654317759725e-10, t, -2.5085949024166185e-08)
p = fma(p, t, 2.7557559627039636e-06)
p = fma(p, t, -0.00019841270630842274)
p = fma(p, t, 0.008333333334519494)
p = fma(p, t, -0.1666666666667311)
p = fma(p, t, 1.0000000000000024)
s = mul(x, p)
```

Chebyshev-fit near-minimax on the quadrant; SLEEF u10 adds double-double reduction for ~1 ulp total

### cos-taylor6

```
t = mul(x, x)
p = fma(-0.001388888888888889, t, 0.041666666666666664)
p = fma(p, t, -0.5)
c = fma(p, t, 1.0)
```

plain Taylor: cheap, inaccurate; the ladder shows why libraries use minimax

### cos-taylor8

```
t = mul(x, x)
p = fma(2.48015873015873e-05, t, -0.001388888888888889)
p = fma(p, t, 0.041666666666666664)
p = fma(p, t, -0.5)
c = fma(p, t, 1.0)
```

plain Taylor: cheap, inaccurate; the ladder shows why libraries use minimax

### cos-taylor10

```
t = mul(x, x)
p = fma(-2.755731922398589e-07, t, 2.48015873015873e-05)
p = fma(p, t, -0.001388888888888889)
p = fma(p, t, 0.041666666666666664)
p = fma(p, t, -0.5)
c = fma(p, t, 1.0)
```

plain Taylor: cheap, inaccurate; the ladder shows why libraries use minimax

### cos-quad-cheb8

```
t = mul(x, x)
p = fma(2.4379853622539965e-05, t, -0.0013886582374563101)
p = fma(p, t, 0.04166661338080217)
p = fma(p, t, -0.49999999530797495)
p = fma(p, t, 0.9999999999035767)
c = p
```

Chebyshev-fit near-minimax on the quadrant

### cos-quad-cheb12

```
t = mul(x, x)
p = fma(2.075686512301728e-09, t, -2.755754941168432e-07)
p = fma(p, t, 2.4801594359371055e-05)
p = fma(p, t, -0.0013888888919297226)
p = fma(p, t, 0.041666666667141194)
p = fma(p, t, -0.5000000000000183)
p = fma(p, t, 1.0000000000000024)
c = p
```

Chebyshev-fit near-minimax on the quadrant

### exp-taylor5

```
p = fma(0.008333333333333333, x, 0.041666666666666664)
p = fma(p, x, 0.16666666666666666)
p = fma(p, x, 0.5)
p = fma(p, x, 1.0)
e = fma(p, x, 1.0)
```

range-reduce with k = round(x/ln2); a plain split loses accuracy for large |x| (hi/lo ln2 needed)

### exp-taylor7

```
p = fma(0.0001984126984126984, x, 0.001388888888888889)
p = fma(p, x, 0.008333333333333333)
p = fma(p, x, 0.041666666666666664)
p = fma(p, x, 0.16666666666666666)
p = fma(p, x, 0.5)
p = fma(p, x, 1.0)
e = fma(p, x, 1.0)
```

range-reduce with k = round(x/ln2); a plain split loses accuracy for large |x| (hi/lo ln2 needed)

### exp-taylor9

```
p = fma(2.7557319223985893e-06, x, 2.48015873015873e-05)
p = fma(p, x, 0.0001984126984126984)
p = fma(p, x, 0.001388888888888889)
p = fma(p, x, 0.008333333333333333)
p = fma(p, x, 0.041666666666666664)
p = fma(p, x, 0.16666666666666666)
p = fma(p, x, 0.5)
p = fma(p, x, 1.0)
e = fma(p, x, 1.0)
```

range-reduce with k = round(x/ln2); a plain split loses accuracy for large |x| (hi/lo ln2 needed)

### exp-cheb7

```
p = fma(0.00019911475068801679, x, 0.0013944595309953014)
p = fma(p, x, 0.008333274273953764)
p = fma(p, x, 0.041666280414681296)
p = fma(p, x, 0.1666666684860883)
p = fma(p, x, 0.5000000084377764)
p = fma(p, x, 0.9999999999850977)
p = fma(p, x, 0.9999999999718296)
e = p
```

Chebyshev-fit near-minimax on the reduced interval; AVX-512 scalef / SVE svscale do the 2^k scaling natively

### exp-cheb9

```
p = fma(2.7621924093449325e-06, x, 2.4880480101392753e-05)
p = fma(p, x, 0.00019841220780010156)
p = fma(p, x, 0.0013888810368452474)
p = fma(p, x, 0.008333333340513734)
p = fma(p, x, 0.041666666983188175)
p = fma(p, x, 0.16666666666690777)
p = fma(p, x, 0.4999999999955776)
p = fma(p, x, 0.999999999999999)
p = fma(p, x, 0.9999999999999974)
e = p
```

Chebyshev-fit near-minimax on the reduced interval; AVX-512 scalef / SVE svscale do the 2^k scaling natively

### exp-cheb11

```
p = fma(1.844358816003227e-08, x, 2.602575079151341e-07)
p = fma(p, x, 2.758190600711796e-06)
p = fma(p, x, 2.480636400388668e-05)
p = fma(p, x, 0.0001984123562888061)
p = fma(p, x, 0.0013888883712549222)
p = fma(p, x, 0.008333333355674174)
p = fma(p, x, 0.041666666689645776)
p = fma(p, x, 0.16666666666597701)
p = fma(p, x, 0.49999999999964856)
p = fma(p, x, 1.0000000000000089)
p = fma(p, x, 0.9999999999999883)
e = p
```

Chebyshev-fit near-minimax on the reduced interval; AVX-512 scalef / SVE svscale do the 2^k scaling natively

## Vector math library calls

| ISA | dtype | op | libmvec | SVML | SLEEF |
|---|---|---|---|---|---|
| avx2 | f64 | exp | `_ZGVdN4v_exp` | `_mm256_exp_pd` | `Sleef_expd4_u10` |
| avx2 | f64 | sin | `_ZGVdN4v_sin` | `_mm256_sin_pd` | `Sleef_sind4_u10` |
| avx2 | f64 | cos | `_ZGVdN4v_cos` | `_mm256_cos_pd` | `Sleef_cosd4_u10` |
| avx2 | f32 | exp | `_ZGVdN8v_expf` | `_mm256_exp_ps` | `Sleef_expf8_u10` |
| avx2 | f32 | sin | `_ZGVdN8v_sinf` | `_mm256_sin_ps` | `Sleef_sinf8_u10` |
| avx2 | f32 | cos | `_ZGVdN8v_cosf` | `_mm256_cos_ps` | `Sleef_cosf8_u10` |
| avx512 | f64 | exp | `_ZGVeN8v_exp` | `_mm512_exp_pd` | `Sleef_expd8_u10avx512f` |
| avx512 | f64 | sin | `_ZGVeN8v_sin` | `_mm512_sin_pd` | `Sleef_sind8_u10avx512f` |
| avx512 | f64 | cos | `_ZGVeN8v_cos` | `_mm512_cos_pd` | `Sleef_cosd8_u10avx512f` |
| avx512 | f32 | exp | `_ZGVeN16v_expf` | `_mm512_exp_ps` | `Sleef_expf16_u10avx512f` |
| avx512 | f32 | sin | `_ZGVeN16v_sinf` | `_mm512_sin_ps` | `Sleef_sinf16_u10avx512f` |
| avx512 | f32 | cos | `_ZGVeN16v_cosf` | `_mm512_cos_ps` | `Sleef_cosf16_u10avx512f` |
| neon | f64 | exp | `—` | `—` | `Sleef_expd2_u10` |
| neon | f64 | sin | `—` | `—` | `Sleef_sind2_u10` |
| neon | f64 | cos | `—` | `—` | `Sleef_cosd2_u10` |
| neon | f32 | exp | `—` | `—` | `Sleef_expf4_u10` |
| neon | f32 | sin | `—` | `—` | `Sleef_sinf4_u10` |
| neon | f32 | cos | `—` | `—` | `Sleef_cosf4_u10` |
| sve | f64 | exp | `—` | `—` | `—` |
| sve | f64 | sin | `—` | `—` | `—` |
| sve | f64 | cos | `—` | `—` | `—` |
| sve | f32 | exp | `—` | `—` | `—` |
| sve | f32 | sin | `—` | `—` | `—` |
| sve | f32 | cos | `—` | `—` | `—` |
