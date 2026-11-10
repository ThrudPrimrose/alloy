# Math kernels — functions as intrinsics (generated, do not edit)

Every function comes as a ladder of C functions built from intrinsics; copy one into the loop's translation unit and the call disappears. Get them with `python -m alloy.isa kernel <isa> <function> <dtype>`; add `--max-ulp N` or `--max-abs E` for the cheapest one that holds a bound.

- **strict**: libm's answer on every special input: NaN, infinities, signed zeros, subnormals and huge arguments are correct, and lanes the vector path cannot hold take one cold branch to scalar libm. Other inputs are within the listed ulp, which is not lower than `relaxed`'s: strict guarantees the domain.
- **relaxed**: no branch. Holds under the contract below and gives garbage outside it. Pick it when the inputs are known finite and in range.
- **fast**: `relaxed` at a lower degree, about half the digits. Pick it when the result feeds a tolerance, an activation, or a first guess.
- **mid3, mid2, mid1**: the rungs between `relaxed` and `fast`, `relaxed`'s program at lower degrees. A function has only the rungs whose degree differs, numbered from the cheapest up.

`strict` is a compile error under `-ffast-math` or `-fassociative-math`: reassociation undoes its error compensation; so is every `log1p`, which has no kernel under reassociation: call the library there. The `relaxed` `pow` carries its logarithm as a double word and refuses the same way: take the next rung down there. The other `relaxed` and `fast` kernels build under both at up to 2.5 times the listed error. `relaxed` and `fast` do not preserve the sign of a zero, and a kernel's division may raise FP flags on valid input.

Inline them only when the loop has other work: the gain over a library call is the call and its spills. It is not universal: `atan` and AVX2 `sinh` lose to the libraries, and SVML `exp` and `pow` are about even. All kernels beat scalar libm by 4x to 13x. `python -m alloy.isa time <isa> <function> <dtype>` measures every rung and the library calls on the machine at hand. ULP is the worst error against a wider libm: over every input of the range for a one-argument f32 kernel (marked `all`), sampled for the others, where it is not a proven bound.

| function | dtype | level | ulp | inputs | intrinsics (avx512) | branch | contract |
|---|---|---|---:|---|---:|---|---|
| sin | f64 | strict | 2.58 | sampled | 64 | cold | any input; vector path for finite, \|x\| <= 1.04858e+06 |
| sin | f64 | relaxed | 1.61 | sampled | 33 | none | finite, \|x\| <= 1.04858e+06 |
| sin | f64 | mid2 | 3.09 | sampled | 31 | none | finite, \|x\| <= 1.04858e+06 |
| sin | f64 | mid1 | 617 | sampled | 29 | none | finite, \|x\| <= 1.04858e+06 |
| sin | f64 | fast | 2.12e+05 | sampled | 25 | none | finite, \|x\| <= 1.04858e+06 |
| sin | f32 | strict | 2.98 | all | 56 | cold | any input; vector path for finite, \|x\| <= 8192 |
| sin | f32 | relaxed | 1.8 | all | 25 | none | finite, \|x\| <= 8192 |
| sin | f32 | mid1 | 20.5 | all | 23 | none | finite, \|x\| <= 8192 |
| sin | f32 | fast | 688 | all | 21 | none | finite, \|x\| <= 8192 |
| cos | f64 | strict | 2.62 | sampled | 74 | cold | any input; vector path for finite, \|x\| <= 1.04858e+06 |
| cos | f64 | relaxed | 1.62 | sampled | 41 | none | finite, \|x\| <= 1.04858e+06 |
| cos | f64 | mid2 | 3.12 | sampled | 39 | none | finite, \|x\| <= 1.04858e+06 |
| cos | f64 | mid1 | 617 | sampled | 37 | none | finite, \|x\| <= 1.04858e+06 |
| cos | f64 | fast | 2.12e+05 | sampled | 33 | none | finite, \|x\| <= 1.04858e+06 |
| cos | f32 | strict | 2.9 | all | 66 | cold | any input; vector path for finite, \|x\| <= 8192 |
| cos | f32 | relaxed | 1.79 | all | 33 | none | finite, \|x\| <= 8192 |
| cos | f32 | mid1 | 20.5 | all | 31 | none | finite, \|x\| <= 8192 |
| cos | f32 | fast | 688 | all | 29 | none | finite, \|x\| <= 8192 |
| tan | f64 | strict | 1.71 | sampled | 80 | cold | any input; vector path for finite, \|x\| <= 1.04858e+06 |
| tan | f64 | relaxed | 3.6 | sampled | 49 | none | finite, \|x\| <= 1.04858e+06 |
| tan | f64 | mid3 | 292 | sampled | 45 | none | finite, \|x\| <= 1.04858e+06 |
| tan | f64 | mid2 | 4.08e+03 | sampled | 43 | none | finite, \|x\| <= 1.04858e+06 |
| tan | f64 | mid1 | 8.02e+05 | sampled | 39 | none | finite, \|x\| <= 1.04858e+06 |
| tan | f64 | fast | 1.59e+08 | sampled | 33 | none | finite, \|x\| <= 1.04858e+06 |
| tan | f32 | strict | 1.74 | all | 66 | cold | any input; vector path for finite, \|x\| <= 8192 |
| tan | f32 | relaxed | 2.75 | all | 35 | none | finite, \|x\| <= 8192 |
| tan | f32 | mid2 | 5.85 | all | 33 | none | finite, \|x\| <= 8192 |
| tan | f32 | mid1 | 61.2 | all | 31 | none | finite, \|x\| <= 8192 |
| tan | f32 | fast | 985 | all | 27 | none | finite, \|x\| <= 8192 |
| exp | f64 | strict | 0.814 | sampled | 51 | cold | any input; vector path for finite, \|x\| <= 700 |
| exp | f64 | relaxed | 0.878 | sampled | 38 | none | finite, \|x\| <= 700 |
| exp | f64 | mid3 | 3.15 | sampled | 36 | none | finite, \|x\| <= 700 |
| exp | f64 | mid2 | 9.58e+03 | sampled | 32 | none | finite, \|x\| <= 700 |
| exp | f64 | mid1 | 4.47e+05 | sampled | 30 | none | finite, \|x\| <= 700 |
| exp | f64 | fast | 2.43e+07 | sampled | 28 | none | finite, \|x\| <= 700 |
| exp | f32 | strict | 0.879 | all | 41 | cold | any input; vector path for finite, \|x\| <= 87 |
| exp | f32 | relaxed | 0.89 | all | 28 | none | finite, \|x\| <= 87 |
| exp | f32 | mid1 | 2.25 | all | 26 | none | finite, \|x\| <= 87 |
| exp | f32 | fast | 72.8 | all | 24 | none | finite, \|x\| <= 87 |
| exp2 | f64 | strict | 0.866 | sampled | 49 | cold | any input; vector path for finite, \|x\| <= 1009.9 |
| exp2 | f64 | relaxed | 0.972 | sampled | 36 | none | finite, \|x\| <= 1009.9 |
| exp2 | f64 | mid3 | 2.66 | sampled | 34 | none | finite, \|x\| <= 1009.9 |
| exp2 | f64 | mid2 | 7.5e+03 | sampled | 30 | none | finite, \|x\| <= 1009.9 |
| exp2 | f64 | mid1 | 4e+05 | sampled | 28 | none | finite, \|x\| <= 1009.9 |
| exp2 | f64 | fast | 1.75e+07 | sampled | 26 | none | finite, \|x\| <= 1009.9 |
| exp2 | f32 | strict | 0.954 | all | 37 | cold | any input; vector path for finite, \|x\| <= 125.51 |
| exp2 | f32 | relaxed | 2.11 | all | 24 | none | finite, \|x\| <= 125.51 |
| exp2 | f32 | fast | 45 | all | 22 | none | finite, \|x\| <= 125.51 |
| exp10 | f64 | strict | 1.1 | sampled | 49 | cold | any input; vector path for finite, \|x\| <= 304.01 |
| exp10 | f64 | relaxed | 1.02 | sampled | 36 | none | finite, \|x\| <= 304.01 |
| exp10 | f64 | mid3 | 2.74 | sampled | 34 | none | finite, \|x\| <= 304.01 |
| exp10 | f64 | mid2 | 7.5e+03 | sampled | 30 | none | finite, \|x\| <= 304.01 |
| exp10 | f64 | mid1 | 4e+05 | sampled | 28 | none | finite, \|x\| <= 304.01 |
| exp10 | f64 | fast | 1.75e+07 | sampled | 26 | none | finite, \|x\| <= 304.01 |
| exp10 | f32 | strict | 1.04 | all | 37 | cold | any input; vector path for finite, \|x\| <= 37.784 |
| exp10 | f32 | relaxed | 2.19 | all | 24 | none | finite, \|x\| <= 37.784 |
| exp10 | f32 | fast | 45 | all | 22 | none | finite, \|x\| <= 37.784 |
| expm1 | f64 | strict | 1.46 | sampled | 59 | cold | any input; vector path for finite, -40 <= x <= 700 |
| expm1 | f64 | relaxed | 1.66 | sampled | 41 | none | finite, -40 <= x <= 700 |
| expm1 | f64 | mid3 | 16.8 | sampled | 39 | none | finite, -40 <= x <= 700 |
| expm1 | f64 | mid2 | 879 | sampled | 37 | none | finite, -40 <= x <= 700 |
| expm1 | f64 | mid1 | 5.62e+04 | sampled | 35 | none | finite, -40 <= x <= 700 |
| expm1 | f64 | fast | 2.51e+06 | sampled | 33 | none | finite, -40 <= x <= 700 |
| expm1 | f32 | strict | 1.49 | all | 49 | cold | any input; vector path for finite, -18 <= x <= 87 |
| expm1 | f32 | relaxed | 1.56 | all | 31 | none | finite, -18 <= x <= 87 |
| expm1 | f32 | fast | 9.48 | all | 29 | none | finite, -18 <= x <= 87 |
| log | f64 | strict | 0.838 | sampled | 56 | cold | any input; vector path for finite, positive, normal |
| log | f64 | relaxed | 0.838 | sampled | 41 | none | finite, positive, normal |
| log | f64 | mid3 | 2.35 | sampled | 39 | none | finite, positive, normal |
| log | f64 | mid2 | 276 | sampled | 37 | none | finite, positive, normal |
| log | f64 | mid1 | 3.63e+04 | sampled | 35 | none | finite, positive, normal |
| log | f64 | fast | 7.43e+06 | sampled | 33 | none | finite, positive, normal |
| log | f32 | strict | 0.897 | all | 48 | cold | any input; vector path for finite, positive, normal |
| log | f32 | relaxed | 0.911 | all | 33 | none | finite, positive, normal |
| log | f32 | fast | 2.94 | all | 31 | none | finite, positive, normal |
| log2 | f64 | strict | 1.23 | sampled | 57 | cold | any input; vector path for finite, positive, normal |
| log2 | f64 | relaxed | 1.23 | sampled | 42 | none | finite, positive, normal |
| log2 | f64 | mid3 | 2.62 | sampled | 40 | none | finite, positive, normal |
| log2 | f64 | mid2 | 279 | sampled | 38 | none | finite, positive, normal |
| log2 | f64 | mid1 | 4.46e+04 | sampled | 36 | none | finite, positive, normal |
| log2 | f64 | fast | 6.96e+06 | sampled | 34 | none | finite, positive, normal |
| log2 | f32 | strict | 1.37 | all | 49 | cold | any input; vector path for finite, positive, normal |
| log2 | f32 | relaxed | 1.37 | all | 34 | none | finite, positive, normal |
| log2 | f32 | fast | 3.38 | all | 32 | none | finite, positive, normal |
| log10 | f64 | strict | 1.14 | sampled | 62 | cold | any input; vector path for finite, positive, normal |
| log10 | f64 | relaxed | 1.14 | sampled | 47 | none | finite, positive, normal |
| log10 | f64 | mid3 | 2.56 | sampled | 45 | none | finite, positive, normal |
| log10 | f64 | mid2 | 279 | sampled | 43 | none | finite, positive, normal |
| log10 | f64 | mid1 | 4.38e+04 | sampled | 41 | none | finite, positive, normal |
| log10 | f64 | fast | 6.54e+06 | sampled | 39 | none | finite, positive, normal |
| log10 | f32 | strict | 1.4 | all | 54 | cold | any input; vector path for finite, positive, normal |
| log10 | f32 | relaxed | 1.4 | all | 39 | none | finite, positive, normal |
| log10 | f32 | fast | 3.81 | all | 37 | none | finite, positive, normal |
| log1p | f64 | strict | 0.832 | sampled | 66 | cold | any input; vector path for finite, x > -1 |
| log1p | f64 | relaxed | 0.877 | sampled | 48 | none | finite, x > -1 |
| log1p | f64 | mid3 | 2.34 | sampled | 46 | none | finite, x > -1 |
| log1p | f64 | mid2 | 276 | sampled | 44 | none | finite, x > -1 |
| log1p | f64 | mid1 | 3.63e+04 | sampled | 42 | none | finite, x > -1 |
| log1p | f64 | fast | 7.43e+06 | sampled | 40 | none | finite, x > -1 |
| log1p | f32 | strict | 0.965 | all | 58 | cold | any input; vector path for finite, x > -1 |
| log1p | f32 | relaxed | 0.971 | all | 40 | none | finite, x > -1 |
| log1p | f32 | fast | 3.01 | all | 38 | none | finite, x > -1 |
| pow | f64 | strict | 1.38 | sampled | 128 | cold | any input; vector path for x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f64 | relaxed | 1.35 | sampled | 103 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f64 | mid3 | 508 | sampled | 76 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f64 | mid2 | 1.16e+04 | sampled | 70 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f64 | mid1 | 8.06e+05 | sampled | 66 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f64 | fast | 7.76e+07 | sampled | 62 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f32 | strict | 1.3 | sampled | 110 | cold | any input; vector path for x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f32 | relaxed | 1.3 | sampled | 85 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f32 | mid2 | 98.4 | sampled | 62 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f32 | mid1 | 99.4 | sampled | 58 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| pow | f32 | fast | 138 | sampled | 56 | none | x positive normal, finite y, \|y*log(x)\| in exp range |
| fmod | f64 | strict | 0 | sampled | 30 | cold | any input; vector path for finite x, finite non-zero y, \|x/y\| < 2^52 |
| fmod | f64 | relaxed | 0 | sampled | 16 | none | finite x, finite non-zero y, \|x/y\| < 2^52 |
| fmod | f64 | fast | 9.01e+15 | sampled | 3 | none | finite x, finite non-zero y, \|x/y\| < 2^52; near a multiple of y it can be off by \|y\| and take the wrong sign |
| fmod | f32 | strict | 0 | sampled | 30 | cold | any input; vector path for finite x, finite non-zero y, \|x/y\| < 2^23 |
| fmod | f32 | relaxed | 0 | sampled | 16 | none | finite x, finite non-zero y, \|x/y\| < 2^23 |
| fmod | f32 | fast | 1.76e+07 | sampled | 3 | none | finite x, finite non-zero y, \|x/y\| < 2^23; near a multiple of y it can be off by \|y\| and take the wrong sign |
| atan | f64 | strict | 1.39 | sampled | 64 | none | any input; vector path for any input |
| atan | f64 | relaxed | 1.33 | sampled | 62 | none | any input |
| atan | f64 | mid3 | 10 | sampled | 58 | none | any input |
| atan | f64 | mid2 | 2.1e+03 | sampled | 52 | none | any input |
| atan | f64 | mid1 | 5.55e+05 | sampled | 46 | none | any input |
| atan | f64 | fast | 2.3e+07 | sampled | 42 | none | any input |
| atan | f32 | strict | 1.33 | all | 42 | none | any input; vector path for any input |
| atan | f32 | relaxed | 1.39 | all | 40 | none | any input |
| atan | f32 | mid3 | 2.67 | all | 38 | none | any input |
| atan | f32 | mid2 | 10.6 | all | 36 | none | any input |
| atan | f32 | mid1 | 77.8 | all | 34 | none | any input |
| atan | f32 | fast | 591 | all | 32 | none | any input |
| asin | f64 | strict | 2.06 | sampled | 54 | none | any input; vector path for \|x\| <= 1 or NaN out |
| asin | f64 | relaxed | 2.01 | sampled | 52 | none | \|x\| <= 1 or NaN out |
| asin | f64 | mid3 | 4.23 | sampled | 48 | none | \|x\| <= 1 or NaN out |
| asin | f64 | mid2 | 561 | sampled | 44 | none | \|x\| <= 1 or NaN out |
| asin | f64 | mid1 | 1.52e+05 | sampled | 40 | none | \|x\| <= 1 or NaN out |
| asin | f64 | fast | 4.57e+07 | sampled | 36 | none | \|x\| <= 1 or NaN out |
| asin | f32 | strict | 2.29 | all | 38 | none | any input; vector path for \|x\| <= 1 or NaN out |
| asin | f32 | relaxed | 2.36 | all | 36 | none | \|x\| <= 1 or NaN out |
| asin | f32 | mid1 | 3.81 | all | 34 | none | \|x\| <= 1 or NaN out |
| asin | f32 | fast | 32.3 | all | 32 | none | \|x\| <= 1 or NaN out |
| acos | f64 | strict | 1.09 | sampled | 62 | none | any input; vector path for \|x\| <= 1 or NaN out |
| acos | f64 | relaxed | 1.09 | sampled | 60 | none | \|x\| <= 1 or NaN out |
| acos | f64 | mid3 | 3.05 | sampled | 56 | none | \|x\| <= 1 or NaN out |
| acos | f64 | mid2 | 533 | sampled | 52 | none | \|x\| <= 1 or NaN out |
| acos | f64 | mid1 | 1.4e+05 | sampled | 48 | none | \|x\| <= 1 or NaN out |
| acos | f64 | fast | 4.36e+07 | sampled | 44 | none | \|x\| <= 1 or NaN out |
| acos | f32 | strict | 1.06 | all | 46 | none | any input; vector path for \|x\| <= 1 or NaN out |
| acos | f32 | relaxed | 1.13 | all | 44 | none | \|x\| <= 1 or NaN out |
| acos | f32 | mid1 | 2.5 | all | 42 | none | \|x\| <= 1 or NaN out |
| acos | f32 | fast | 29.1 | all | 40 | none | \|x\| <= 1 or NaN out |
| sinh | f64 | strict | 1.57 | sampled | 86 | cold | any input; vector path for finite, \|x\| <= 700 |
| sinh | f64 | relaxed | 1.58 | sampled | 71 | none | finite, \|x\| <= 700 |
| sinh | f64 | mid3 | 3.84 | sampled | 69 | none | finite, \|x\| <= 700 |
| sinh | f64 | mid2 | 1.04e+04 | sampled | 63 | none | finite, \|x\| <= 700 |
| sinh | f64 | mid1 | 4.82e+05 | sampled | 59 | none | finite, \|x\| <= 700 |
| sinh | f64 | fast | 2.65e+07 | sampled | 57 | none | finite, \|x\| <= 700 |
| sinh | f32 | strict | 1.62 | all | 70 | cold | any input; vector path for finite, \|x\| <= 87 |
| sinh | f32 | relaxed | 1.62 | all | 55 | none | finite, \|x\| <= 87 |
| sinh | f32 | mid1 | 117 | all | 51 | none | finite, \|x\| <= 87 |
| sinh | f32 | fast | 117 | all | 49 | none | finite, \|x\| <= 87 |
| cosh | f64 | strict | 1.21 | sampled | 57 | cold | any input; vector path for finite, \|x\| <= 700 |
| cosh | f64 | relaxed | 1.25 | sampled | 44 | none | finite, \|x\| <= 700 |
| cosh | f64 | mid3 | 3.5 | sampled | 42 | none | finite, \|x\| <= 700 |
| cosh | f64 | mid2 | 9.58e+03 | sampled | 38 | none | finite, \|x\| <= 700 |
| cosh | f64 | mid1 | 4.47e+05 | sampled | 36 | none | finite, \|x\| <= 700 |
| cosh | f64 | fast | 2.43e+07 | sampled | 34 | none | finite, \|x\| <= 700 |
| cosh | f32 | strict | 1.33 | all | 47 | cold | any input; vector path for finite, \|x\| <= 87 |
| cosh | f32 | relaxed | 1.36 | all | 34 | none | finite, \|x\| <= 87 |
| cosh | f32 | mid1 | 2.73 | all | 32 | none | finite, \|x\| <= 87 |
| cosh | f32 | fast | 73.3 | all | 30 | none | finite, \|x\| <= 87 |
| tanh | f64 | strict | 2.11 | sampled | 59 | none | any input; vector path for finite |
| tanh | f64 | relaxed | 2.01 | sampled | 57 | none | finite |
| tanh | f64 | mid3 | 12.2 | sampled | 55 | none | finite |
| tanh | f64 | mid2 | 596 | sampled | 53 | none | finite |
| tanh | f64 | mid1 | 4.59e+04 | sampled | 51 | none | finite |
| tanh | f64 | fast | 1.77e+06 | sampled | 49 | none | finite |
| tanh | f32 | strict | 2.42 | all | 49 | none | any input; vector path for finite |
| tanh | f32 | relaxed | 2.61 | all | 47 | none | finite |
| tanh | f32 | fast | 8.15 | all | 45 | none | finite |

## Example: `exp`, f64, relaxed, AVX2

```c
static inline __m256d alloy_exp_f64_relaxed(__m256d x) {
    __m256d q = _mm256_round_pd(_mm256_mul_pd(x, _mm256_set1_pd(1.4426950408889634)), _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
    __m256d rh = _mm256_fnmadd_pd(q, _mm256_set1_pd(0.6931471805599453), x);
    __m256d rl = _mm256_mul_pd(q, _mm256_set1_pd(2.3190468138462996e-17));
    __m256d r = _mm256_sub_pd(rh, rl);
    __m256d t = _mm256_mul_pd(r, r);
    __m256d p = _mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_fmadd_pd(_mm256_set1_pd(2.499896073724044e-08), r, _mm256_set1_pd(2.763168685442278e-07)), r, _mm256_set1_pd(2.755759729968463e-06)), r, _mm256_set1_pd(2.480148935437509e-05)), r, _mm256_set1_pd(0.00019841269486020185)), r, _mm256_set1_pd(0.001388888894691698)), r, _mm256_set1_pd(0.008333333333507734)), r, _mm256_set1_pd(0.04166666666651917)), r, _mm256_set1_pd(0.16666666666666385)), r, _mm256_set1_pd(0.5000000000000012));
    __m256d m = _mm256_add_pd(_mm256_set1_pd(1.0), _mm256_add_pd(rh, _mm256_sub_pd(_mm256_mul_pd(t, p), rl)));
    __m256d e = _mm256_castsi256_pd(_mm256_add_epi64(_mm256_castpd_si256(m), _mm256_slli_epi64(_mm256_sub_epi64(_mm256_castpd_si256(_mm256_add_pd(q, _mm256_set1_pd(0x1.8p52))), _mm256_castpd_si256(_mm256_set1_pd(0x1.8p52))), 52)));
    return e;
}
```
