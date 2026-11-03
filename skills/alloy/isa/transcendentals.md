# Transcendentals — polynomial tiers with measured ULP (generated, do not edit)

Error in units of 2^-52 at function scale: max \|approx - ref\| / spacing(max(\|ref\|, 1.0)) against double-precision libm on dense grids, so real f64 ulp is up to 2.7x larger and f32 rows get the same f64 figures. A tier holds on a reduced domain only: `kernel` gives whole functions with true ulp. Recipes are Horner schemes in abstract-op steps (`fma`/`mul` with inline coefficients) — copyable implementations.

| tier | op | domain | error (ulp) | error (abs) |
|---|---|---|---|---|
| `sin-taylor7` | sin | \|x\| <= pi/2 after Cody-Waite reduction | 7.066e+11 | 0.000157 |
| `sin-taylor9` | sin | \|x\| <= pi/2 after Cody-Waite reduction | 1.595e+10 | 3.54e-06 |
| `sin-taylor11` | sin | \|x\| <= pi/2 after Cody-Waite reduction | 2.534e+08 | 5.63e-08 |
| `sin-quad-cheb9` | sin | \|x\| <= pi/4 after quadrant (mod pi/2) reduction | 1.524e+04 | 3.38e-12 |
| `sin-quad-cheb13` | sin | \|x\| <= pi/4 after quadrant (mod pi/2) reduction | 0.5 | 1.11e-16 |
| `cos-taylor6` | cos | \|x\| <= pi/2 after Cody-Waite reduction | 4.029e+12 | 0.000895 |
| `cos-taylor8` | cos | \|x\| <= pi/2 after Cody-Waite reduction | 1.114e+11 | 2.47e-05 |
| `cos-taylor10` | cos | \|x\| <= pi/2 after Cody-Waite reduction | 2.093e+09 | 4.65e-07 |
| `cos-quad-cheb8` | cos | \|x\| <= pi/4 after quadrant (mod pi/2) reduction | 2.14e+05 | 4.75e-11 |
| `cos-quad-cheb12` | cos | \|x\| <= pi/4 after quadrant (mod pi/2) reduction | 1 | 2.22e-16 |
| `exp-taylor5` | exp | \|x\| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 1.14e+10 | 2.53e-06 |
| `exp-taylor7` | exp | \|x\| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 2.418e+07 | 5.37e-09 |
| `exp-taylor9` | exp | \|x\| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 3.203e+04 | 7.11e-12 |
| `exp-cheb7` | exp | \|x\| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 1.894e+05 | 4.21e-11 |
| `exp-cheb9` | exp | \|x\| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 64 | 1.42e-14 |
| `exp-cheb11` | exp | \|x\| <= ln(2)/2 after k-split: x = k*ln2 + r; scale by 2^k after | 1 | 2.22e-16 |
| `log-taylor5` | log | \|x\| <= 3-2*sqrt(2), x = (m-1)/(m+1), after the split v = 2^e*m with m in [sqrt(1/2), sqrt(2)]; add e*ln2 after | 5.764e+09 | 1.28e-06 |
| `log-taylor7` | log | \|x\| <= 3-2*sqrt(2), x = (m-1)/(m+1), after the split v = 2^e*m with m in [sqrt(1/2), sqrt(2)]; add e*ln2 after | 1.321e+08 | 2.93e-08 |
| `log-taylor9` | log | \|x\| <= 3-2*sqrt(2), x = (m-1)/(m+1), after the split v = 2^e*m with m in [sqrt(1/2), sqrt(2)]; add e*ln2 after | 3.185e+06 | 7.07e-10 |
| `log-cheb7` | log | \|x\| <= 3-2*sqrt(2), x = (m-1)/(m+1), after the split v = 2^e*m with m in [sqrt(1/2), sqrt(2)]; add e*ln2 after | 1.084e+06 | 2.41e-10 |
| `log-cheb11` | log | \|x\| <= 3-2*sqrt(2), x = (m-1)/(m+1), after the split v = 2^e*m with m in [sqrt(1/2), sqrt(2)]; add e*ln2 after | 42 | 9.33e-15 |
| `log-cheb13` | log | \|x\| <= 3-2*sqrt(2), x = (m-1)/(m+1), after the split v = 2^e*m with m in [sqrt(1/2), sqrt(2)]; add e*ln2 after | 0.75 | 1.67e-16 |

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
p = fma(2.7173456841089953e-06, t, -0.000198392022122311)
p = fma(p, t, 0.00833332878245888)
p = fma(p, t, -0.16666666631591165)
p = fma(p, t, 0.9999999999956731)
s = mul(x, p)
```

Chebyshev fit on the quadrant; SLEEF u10 adds double-double reduction for ~1 ulp total

### sin-quad-cheb13

```
t = mul(x, x)
p = fma(1.5894736651849094e-10, t, -2.5050716974102745e-08)
p = fma(p, t, 2.755731337640013e-06)
p = fma(p, t, -0.000198412698286503)
p = fma(p, t, 0.008333333333320363)
p = fma(p, t, -0.16666666666666616)
p = fma(p, t, 1.0)
s = mul(x, p)
```

Chebyshev fit on the quadrant; SLEEF u10 adds double-double reduction for ~1 ulp total

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
p = fma(2.4379831251175367e-05, t, -0.0013886617999647076)
p = fma(p, t, 0.041666616692532826)
p = fma(p, t, -0.4999999961485761)
p = fma(p, t, 0.9999999999524894)
c = p
```

Chebyshev fit on the quadrant

### cos-quad-cheb12

```
t = mul(x, x)
p = fma(2.0630454379662294e-09, t, -2.755523388484742e-07)
p = fma(p, t, 2.4801578538562985e-05)
p = fma(p, t, -0.0013888888869978658)
p = fma(p, t, 0.041666666666472306)
p = fma(p, t, -0.4999999999999925)
p = fma(p, t, 1.0)
c = p
```

Chebyshev fit on the quadrant

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
p = fma(0.00019907569310848288, x, 0.0013948578326459795)
p = fma(p, x, 0.008333283538708528)
p = fma(p, x, 0.041666218319291945)
p = fma(p, x, 0.16666666786308587)
p = fma(p, x, 0.5000000107729166)
p = fma(p, x, 0.999999999995509)
p = fma(p, x, 0.9999999999595618)
e = p
```

Chebyshev fit on the reduced interval; AVX-512 scalef / SVE svscale do the 2^k scaling natively

### exp-cheb9

```
p = fma(2.7632640675430236e-06, x, 2.4884459751751116e-05)
p = fma(p, x, 0.0001984119064754424)
p = fma(p, x, 0.0013888801749656543)
p = fma(p, x, 0.008333333367311603)
p = fma(p, x, 0.04166666704055191)
p = fma(p, x, 0.16666666666615648)
p = fma(p, x, 0.4999999999943859)
p = fma(p, x, 1.0000000000000013)
p = fma(p, x, 1.0000000000000135)
e = p
```

Chebyshev fit on the reduced interval; AVX-512 scalef / SVE svscale do the 2^k scaling natively

### exp-cheb11

```
p = fma(2.5110037605963777e-08, x, 2.763263963904103e-07)
p = fma(p, x, 2.755724091857897e-06)
p = fma(p, x, 2.4801485482328494e-05)
p = fma(p, x, 0.00019841269890047113)
p = fma(p, x, 0.0013888888952314775)
p = fma(p, x, 0.008333333333319601)
p = fma(p, x, 0.0416666666664881)
p = fma(p, x, 0.1666666666666668)
p = fma(p, x, 0.5000000000000019)
p = fma(p, x, 1.0)
p = fma(p, x, 1.0)
e = p
```

Chebyshev fit on the reduced interval; AVX-512 scalef / SVE svscale do the 2^k scaling natively

### log-taylor5

```
t = mul(x, x)
p = fma(0.4, t, 0.6666666666666666)
l = fma(mul(x, t), p, mul(2.0, x))
```

plain atanh series: cheap, inaccurate; the ladder shows why libraries use minimax

### log-taylor7

```
t = mul(x, x)
p = fma(0.2857142857142857, t, 0.4)
p = fma(p, t, 0.6666666666666666)
l = fma(mul(x, t), p, mul(2.0, x))
```

plain atanh series: cheap, inaccurate; the ladder shows why libraries use minimax

### log-taylor9

```
t = mul(x, x)
p = fma(0.2222222222222222, t, 0.2857142857142857)
p = fma(p, t, 0.4)
p = fma(p, t, 0.6666666666666666)
l = fma(mul(x, t), p, mul(2.0, x))
```

plain atanh series: cheap, inaccurate; the ladder shows why libraries use minimax

### log-cheb7

```
t = mul(x, x)
p = fma(0.29924390479144986, t, 0.3997485051751905)
p = fma(p, t, 0.6666681533815119)
p = fma(p, t, 1.9999999986313182)
l = mul(x, p)
```

Chebyshev fit in t = x*x; the division in x = (m-1)/(m+1) is the cost a table lookup avoids

### log-cheb11

```
t = mul(x, x)
p = fma(0.19608095639753054, t, 0.2217424991007749)
p = fma(p, t, 0.28572166145875727)
p = fma(p, t, 0.3999999489183238)
p = fma(p, t, 0.6666666667957926)
p = fma(p, t, 1.9999999999999472)
l = mul(x, p)
```

Chebyshev fit in t = x*x; the division in x = (m-1)/(m+1) is the cost a table lookup avoids

### log-cheb13

```
t = mul(x, x)
p = fma(0.16837659970680488, t, 0.18121934431215214)
p = fma(p, t, 0.22223434547517906)
p = fma(p, t, 0.2857141602110767)
p = fma(p, t, 0.40000000061741614)
p = fma(p, t, 0.6666666666655292)
p = fma(p, t, 2.0000000000000004)
l = mul(x, p)
```

Chebyshev fit in t = x*x; the division in x = (m-1)/(m+1) is the cost a table lookup avoids

## Vector math library calls

| ISA | dtype | op | libmvec | SVML | SLEEF |
|---|---|---|---|---|---|
| avx2 | f64 | exp | `_ZGVdN4v_exp` | `__svml_exp4` | `Sleef_expd4_u10avx2` |
| avx2 | f64 | sin | `_ZGVdN4v_sin` | `__svml_sin4` | `Sleef_sind4_u10avx2` |
| avx2 | f64 | cos | `_ZGVdN4v_cos` | `__svml_cos4` | `Sleef_cosd4_u10avx2` |
| avx2 | f32 | exp | `_ZGVdN8v_expf` | `__svml_expf8` | `Sleef_expf8_u10avx2` |
| avx2 | f32 | sin | `_ZGVdN8v_sinf` | `__svml_sinf8` | `Sleef_sinf8_u10avx2` |
| avx2 | f32 | cos | `_ZGVdN8v_cosf` | `__svml_cosf8` | `Sleef_cosf8_u10avx2` |
| avx512 | f64 | exp | `_ZGVeN8v_exp` | `__svml_exp8` | `Sleef_expd8_u10avx512f` |
| avx512 | f64 | sin | `_ZGVeN8v_sin` | `__svml_sin8` | `Sleef_sind8_u10avx512f` |
| avx512 | f64 | cos | `_ZGVeN8v_cos` | `__svml_cos8` | `Sleef_cosd8_u10avx512f` |
| avx512 | f32 | exp | `_ZGVeN16v_expf` | `__svml_expf16` | `Sleef_expf16_u10avx512f` |
| avx512 | f32 | sin | `_ZGVeN16v_sinf` | `__svml_sinf16` | `Sleef_sinf16_u10avx512f` |
| avx512 | f32 | cos | `_ZGVeN16v_cosf` | `__svml_cosf16` | `Sleef_cosf16_u10avx512f` |
| neon | f64 | exp | `_ZGVnN2v_exp` | `—` | `Sleef_expd2_u10` |
| neon | f64 | sin | `_ZGVnN2v_sin` | `—` | `Sleef_sind2_u10` |
| neon | f64 | cos | `_ZGVnN2v_cos` | `—` | `Sleef_cosd2_u10` |
| neon | f32 | exp | `_ZGVnN4v_expf` | `—` | `Sleef_expf4_u10` |
| neon | f32 | sin | `_ZGVnN4v_sinf` | `—` | `Sleef_sinf4_u10` |
| neon | f32 | cos | `_ZGVnN4v_cosf` | `—` | `Sleef_cosf4_u10` |
| sve | f64 | exp | `_ZGVsMxv_exp` | `—` | `—` |
| sve | f64 | sin | `_ZGVsMxv_sin` | `—` | `—` |
| sve | f64 | cos | `_ZGVsMxv_cos` | `—` | `—` |
| sve | f32 | exp | `_ZGVsMxv_expf` | `—` | `—` |
| sve | f32 | sin | `_ZGVsMxv_sinf` | `—` | `—` |
| sve | f32 | cos | `_ZGVsMxv_cosf` | `—` | `—` |
