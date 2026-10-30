# Math kernels — functions as intrinsics (generated, do not edit)

Every function comes as three C functions built from intrinsics; copy one into the loop's translation unit and the call disappears. Get them with `python -m alloy.isa kernel <isa> <function> <dtype>`.

- **strict**: matches libm on every input. NaN, infinities, signed zeros, subnormals and huge arguments are correct; lanes the vector path cannot hold take one cold branch to scalar libm. About as accurate as a default library call, not correctly rounded.
- **relaxed**: no branch. Holds under the contract below and gives garbage outside it. Pick it when the inputs are known finite and in range.
- **fast**: `relaxed` at a lower degree, about half the digits. Pick it when the result feeds a tolerance, an activation, or a first guess.

`strict` is a compile error under `-ffast-math` or `-fassociative-math`: reassociation undoes its error compensation; so is every `log1p`. The other `relaxed` and `fast` kernels build under both at up to 2.5 times the listed error.

Inline them only when the loop has other work: the gain over a library call is the call and its spills. ULP is the worst sampled error against a wider libm, not a proven bound.

| function | dtype | level | ulp | intrinsics (avx512) | branch | contract |
|---|---|---|---:|---:|---|---|
| sin | f64 | strict | 2.58 | 64 | cold | finite, |x| <= 1.04858e+06 |
| sin | f64 | relaxed | 1.85 | 33 | none | finite, |x| <= 1.04858e+06 |
| sin | f64 | fast | 9.61e+05 | 25 | none | finite, |x| <= 1.04858e+06 |
| sin | f32 | strict | 2.5 | 56 | cold | finite, |x| <= 8192 |
| sin | f32 | relaxed | 1.95 | 25 | none | finite, |x| <= 8192 |
| sin | f32 | fast | 688 | 21 | none | finite, |x| <= 8192 |
| cos | f64 | strict | 2.62 | 69 | cold | finite, |x| <= 1.04858e+06 |
| cos | f64 | relaxed | 1.79 | 41 | none | finite, |x| <= 1.04858e+06 |
| cos | f64 | fast | 9.61e+05 | 33 | none | finite, |x| <= 1.04858e+06 |
| cos | f32 | strict | 2.5 | 61 | cold | finite, |x| <= 8192 |
| cos | f32 | relaxed | 2.02 | 33 | none | finite, |x| <= 8192 |
| cos | f32 | fast | 688 | 29 | none | finite, |x| <= 8192 |
| tan | f64 | strict | 1.7 | 80 | cold | finite, |x| <= 1.04858e+06 |
| tan | f64 | relaxed | 6.72 | 49 | none | finite, |x| <= 1.04858e+06 |
| tan | f64 | fast | 5.23e+08 | 33 | none | finite, |x| <= 1.04858e+06 |
| tan | f32 | strict | 1.54 | 66 | cold | finite, |x| <= 8192 |
| tan | f32 | relaxed | 2.52 | 35 | none | finite, |x| <= 8192 |
| tan | f32 | fast | 2.63e+03 | 27 | none | finite, |x| <= 8192 |
| exp | f64 | strict | 0.828 | 51 | cold | finite, |x| <= 700 |
| exp | f64 | relaxed | 0.921 | 38 | none | finite, |x| <= 700 |
| exp | f64 | fast | 5.16e+07 | 28 | none | finite, |x| <= 700 |
| exp | f32 | strict | 0.837 | 41 | cold | finite, |x| <= 87 |
| exp | f32 | relaxed | 0.888 | 28 | none | finite, |x| <= 87 |
| exp | f32 | fast | 156 | 24 | none | finite, |x| <= 87 |
| exp2 | f64 | strict | 0.856 | 49 | cold | finite, |x| <= 1009.9 |
| exp2 | f64 | relaxed | 0.861 | 36 | none | finite, |x| <= 1009.9 |
| exp2 | f64 | fast | 3.02e+07 | 26 | none | finite, |x| <= 1009.9 |
| exp2 | f32 | strict | 0.808 | 37 | cold | finite, |x| <= 125.51 |
| exp2 | f32 | relaxed | 2.77 | 24 | none | finite, |x| <= 125.51 |
| exp2 | f32 | fast | 73.1 | 22 | none | finite, |x| <= 125.51 |
| exp10 | f64 | strict | 1.06 | 49 | cold | finite, |x| <= 304.01 |
| exp10 | f64 | relaxed | 1.11 | 36 | none | finite, |x| <= 304.01 |
| exp10 | f64 | fast | 3.02e+07 | 26 | none | finite, |x| <= 304.01 |
| exp10 | f32 | strict | 0.916 | 37 | cold | finite, |x| <= 37.784 |
| exp10 | f32 | relaxed | 2.97 | 24 | none | finite, |x| <= 37.784 |
| exp10 | f32 | fast | 73.6 | 22 | none | finite, |x| <= 37.784 |
| expm1 | f64 | strict | 1.46 | 59 | cold | finite, -40 <= x <= 700 |
| expm1 | f64 | relaxed | 1.66 | 41 | none | finite, -40 <= x <= 700 |
| expm1 | f64 | fast | 4.65e+06 | 33 | none | finite, -40 <= x <= 700 |
| expm1 | f32 | strict | 1.41 | 49 | cold | finite, -18 <= x <= 87 |
| expm1 | f32 | relaxed | 1.64 | 31 | none | finite, -18 <= x <= 87 |
| expm1 | f32 | fast | 18 | 29 | none | finite, -18 <= x <= 87 |
| log | f64 | strict | 0.825 | 56 | cold | finite, positive, normal |
| log | f64 | relaxed | 0.838 | 41 | none | finite, positive, normal |
| log | f64 | fast | 1.46e+07 | 33 | none | finite, positive, normal |
| log | f32 | strict | 0.819 | 48 | cold | finite, positive, normal |
| log | f32 | relaxed | 0.819 | 33 | none | finite, positive, normal |
| log | f32 | fast | 5.85 | 31 | none | finite, positive, normal |
| log2 | f64 | strict | 1.23 | 57 | cold | finite, positive, normal |
| log2 | f64 | relaxed | 1.23 | 42 | none | finite, positive, normal |
| log2 | f64 | fast | 2.1e+07 | 34 | none | finite, positive, normal |
| log2 | f32 | strict | 1.23 | 49 | cold | finite, positive, normal |
| log2 | f32 | relaxed | 1.23 | 34 | none | finite, positive, normal |
| log2 | f32 | fast | 8.48 | 32 | none | finite, positive, normal |
| log10 | f64 | strict | 1.14 | 62 | cold | finite, positive, normal |
| log10 | f64 | relaxed | 1.14 | 47 | none | finite, positive, normal |
| log10 | f64 | fast | 1.61e+07 | 39 | none | finite, positive, normal |
| log10 | f32 | strict | 1.25 | 54 | cold | finite, positive, normal |
| log10 | f32 | relaxed | 1.36 | 39 | none | finite, positive, normal |
| log10 | f32 | fast | 5.51 | 37 | none | finite, positive, normal |
| log1p | f64 | strict | 0.856 | 66 | cold | finite, x > -1 |
| log1p | f64 | relaxed | 0.856 | 48 | none | finite, x > -1 |
| log1p | f64 | fast | 1.46e+07 | 40 | none | finite, x > -1 |
| log1p | f32 | strict | 0.885 | 58 | cold | finite, x > -1 |
| log1p | f32 | relaxed | 0.885 | 40 | none | finite, x > -1 |
| log1p | f32 | fast | 5.79 | 38 | none | finite, x > -1 |
| pow | f64 | strict | 3.05 | 120 | cold | x positive normal, finite y, |y*log(x)| in exp range |
| pow | f64 | relaxed | 509 | 80 | none | x positive normal, finite y, |y*log(x)| in exp range |
| pow | f64 | fast | 8.54e+07 | 62 | none | x positive normal, finite y, |y*log(x)| in exp range |
| pow | f32 | strict | 2.92 | 102 | cold | x positive normal, finite y, |y*log(x)| in exp range |
| pow | f32 | relaxed | 96.3 | 62 | none | x positive normal, finite y, |y*log(x)| in exp range |
| pow | f32 | fast | 190 | 56 | none | x positive normal, finite y, |y*log(x)| in exp range |
| atan | f64 | strict | 1.47 | 64 | none | any input |
| atan | f64 | relaxed | 1.82 | 62 | none | any input |
| atan | f64 | fast | 7.63e+07 | 42 | none | any input |
| atan | f32 | strict | 1.31 | 42 | none | any input |
| atan | f32 | relaxed | 1.91 | 40 | none | any input |
| atan | f32 | fast | 1.8e+03 | 32 | none | any input |
| asin | f64 | strict | 2.01 | 54 | none | |x| <= 1 or NaN out |
| asin | f64 | relaxed | 2.06 | 52 | none | |x| <= 1 or NaN out |
| asin | f64 | fast | 1.63e+08 | 36 | none | |x| <= 1 or NaN out |
| asin | f32 | strict | 2.27 | 38 | none | |x| <= 1 or NaN out |
| asin | f32 | relaxed | 2.38 | 36 | none | |x| <= 1 or NaN out |
| asin | f32 | fast | 105 | 32 | none | |x| <= 1 or NaN out |
| acos | f64 | strict | 1.09 | 62 | none | |x| <= 1 or NaN out |
| acos | f64 | relaxed | 1.09 | 60 | none | |x| <= 1 or NaN out |
| acos | f64 | fast | 1.38e+08 | 44 | none | |x| <= 1 or NaN out |
| acos | f32 | strict | 1.05 | 46 | none | |x| <= 1 or NaN out |
| acos | f32 | relaxed | 1.3 | 44 | none | |x| <= 1 or NaN out |
| acos | f32 | fast | 67.6 | 40 | none | |x| <= 1 or NaN out |
| sinh | f64 | strict | 1.57 | 86 | cold | finite, |x| <= 700 |
| sinh | f64 | relaxed | 2.86 | 71 | none | finite, |x| <= 700 |
| sinh | f64 | fast | 5.8e+07 | 57 | none | finite, |x| <= 700 |
| sinh | f32 | strict | 1.58 | 70 | cold | finite, |x| <= 87 |
| sinh | f32 | relaxed | 1.71 | 55 | none | finite, |x| <= 87 |
| sinh | f32 | fast | 214 | 49 | none | finite, |x| <= 87 |
| cosh | f64 | strict | 1.21 | 57 | cold | finite, |x| <= 700 |
| cosh | f64 | relaxed | 1.29 | 44 | none | finite, |x| <= 700 |
| cosh | f64 | fast | 5.16e+07 | 34 | none | finite, |x| <= 700 |
| cosh | f32 | strict | 1.27 | 47 | cold | finite, |x| <= 87 |
| cosh | f32 | relaxed | 1.27 | 34 | none | finite, |x| <= 87 |
| cosh | f32 | fast | 156 | 30 | none | finite, |x| <= 87 |
| tanh | f64 | strict | 2.11 | 59 | none | finite |
| tanh | f64 | relaxed | 2.15 | 57 | none | finite |
| tanh | f64 | fast | 3.05e+06 | 49 | none | finite |
| tanh | f32 | strict | 2.2 | 49 | none | finite |
| tanh | f32 | relaxed | 2.34 | 47 | none | finite |
| tanh | f32 | fast | 13.1 | 45 | none | finite |

## Example: `exp`, f64, relaxed, AVX2

```c
static inline __m256d alloy_exp_f64_relaxed(__m256d x) {
    __m256d q = _mm256_round_pd(_mm256_mul_pd(x, _mm256_set1_pd(1.4426950408889634)), _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    __m256d rh = _mm256_fnmadd_pd(q, _mm256_set1_pd(0.6931471805599453), x);
    __m256d rl = _mm256_mul_pd(q, _mm256_set1_pd(2.3190468138462996e-17));
    __m256d r = _mm256_sub_pd(rh, rl);
    __m256d t = _mm256_mul_pd(r, r);
    __m256d p = _mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_set1_pd(2.510134692835034e-08), r, _mm256_set1_pd(2.7621338669142925e-07)), r, _mm256_set1_pd(2.75572664186123e-06)), r, _mm256_set1_pd(2.4801518641395993e-05)), r, _mm256_set1_pd(0.00019841269864380513)), r, _mm256_set1_pd(0.0013888888918939168)), r, _mm256_set1_pd(0.008333333333329793)), r, _mm256_set1_pd(0.04166666666662064)), r, _mm256_set1_pd(0.16666666666666669)), r, _mm256_set1_pd(0.5000000000000001));
    __m256d m = _mm256_add_pd(_mm256_set1_pd(1.0), _mm256_add_pd(rh, _mm256_sub_pd(_mm256_mul_pd(t, p), rl)));
    __m256d e = _mm256_castsi256_pd(_mm256_add_epi64(_mm256_castpd_si256(m), _mm256_slli_epi64(_mm256_sub_epi64(_mm256_castpd_si256(_mm256_add_pd(q, _mm256_set1_pd(0x1.8p52))), _mm256_castpd_si256(_mm256_set1_pd(0x1.8p52))), 52)));
    return e;
}
```
