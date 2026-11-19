---
name: alloy-c
description: "The C that Alloy can take as input: one kernel in canonical C form plus the bench's binding JSON. Alloy lifts it to NumPy and then to an SDFG it can tune. Lists what is accepted, what is refused (with the exact reason the lifter prints), and how to rewrite a refused kernel. Read it before handing Alloy a C kernel, or when the lifter refuses one."
when: Before giving Alloy a C file instead of NumPy, and whenever `python -m alloy.frontend.cnumpy` answers `refused: ...`.
---

# C input for Alloy (`alloy.frontend.cnumpy`)

    python -m alloy.frontend.cnumpy kernel.c kernel_binding.json --out kernel_numpy.py --sdfg kernel.sdfg

The lifter reads one C function and the binding the bench writes next to it
(`<kernel>_fp64_binding.json`: `kernel`, then per argument `name`, `kind` such as `ptr_double` or `int64`, and
`shape`). It prints the kernel as canonical NumPy. With `--sdfg` it also writes the SDFG that DaCe parses from that
NumPy. It never guesses: C outside the form below is refused with a reason.

## Canonical C form

- One function, named as the binding's `kernel`. Every parameter is in the binding. It returns `void`, and outputs
  go through pointers.
- Arrays are flat, row-major `T *restrict` pointers. Their shape comes from the binding (`["N", "M"]`). An index
  such as `A[(i)*(M) + (j)]` becomes `A[i, j]`. Integer extents named in a shape count as non-negative.
- Types: `double`, `float`, `bool`, and the integer types (`int64_t`, `int32_t`, `uint8_t`, `int`, `long`, ...).
- Statements: declarations, `=` and compound assignments, `++`/`--`, `for`, `while`, `do`, `if`/`else`, `break`,
  `continue` (inside a `for` over an integer range), and `return;`.
- Temporaries: `T *t = malloc(count * sizeof(T))` or `calloc`, also declared as `NULL` first and allocated later.
  Local arrays work too: `double t[3][3] = {0};`. `free(t)` and allocation checks are dropped.
- Calls: math.h (`sqrt`, `exp`, `fmax`, `pow`, `round`, ... and their `f` forms), `memset(p, 0, n * sizeof(T))`,
  `memcpy`, `cblas_dgemm`/`sgemm`, `cblas_dgemv`/`sgemv` and `cblas_ddot` (row-major, unit stride), and the
  helpers of the bench's prelude (`int_floor`, `python_mod`, `__npb_fmax`, ...).
- File-scope constants: `constexpr int64_t K = 4;`, `static const double D = 0.5;`, and `#define N 64`.

```c
void scale_fp64(double *restrict y, const double *restrict x, const int64_t N, const int64_t M) {
  for (int64_t i = 0; i < N; ++i)
    for (int64_t j = 0; j < M; ++j)
      y[(i)*(M) + (j)] = 2.0 * x[(i)*(M) + (j)];
}
```

becomes `y[:, :] = 2.0 * x`. A `C[i,j] = 0; C[i,j] += A[i,k] * B[k,j]` nest or a `cblas_dgemm` becomes `C[:, :] = A @ B`,
and `s += a[i]` becomes `s += np.sum(a)`. Integer `/` and `%` keep C's truncation through `c_div` and `c_mod`,
unless both operands are provably non-negative.

## Refused, with the reason printed

| reason | rewrite |
|---|---|
| `inline asm` | write the operation in C. Later, asm may come in as special functions: opaque calls the lifter keeps by name. |
| `goto`, `switch` | use `if`/`else` and loops |
| `a type outside canonical C form (a struct, complex or library type)`, `a struct or union`, `complex arithmetic` | split a struct into one array per field, and complex numbers into real and imaginary arrays |
| `a pointer into an array (pointer arithmetic)`, `a pointer dereference or address (pointer arithmetic)`, `a pointer to a pointer` | index the whole array: `A[(i)*(M) + j]`, not `p = A + i*M; p[j]` |
| `a pointer read before it holds a malloc'd array` | allocate before the first use |
| `a call to a helper function of the file (inline it into the kernel)` | inline the helper |
| `a call to a function outside math.h and BLAS`, `a call through a function pointer` | inline it or use a math.h or BLAS call |
| `a name that is no array, scalar or constant (a global or a macro)` | pass it as a parameter, or declare it `constexpr` |
| `an assignment inside an expression`, `an expression statement without effect (or a comma expression)` | one assignment per statement: `a[i] = x; i++;` |
| `continue in a loop without a canonical range` | write the loop as `for (int64_t i = lo; i < hi; ++i)` |
| `a returned value (the C ABI writes outputs through pointers)` | write the result to an output pointer |
| `a memset to a value other than zero`, `a memory call over part of a multidimensional array`, `a memory call on something other than a whole array` | write a loop |
| `a BLAS call with a leading dimension other than the row length`, `a strided BLAS vector`, `a BLAS operand that is no whole array (pointer arithmetic)` | call BLAS on whole arrays, or write the loop nest |
| `a parameter the binding does not name`, `no function of the binding's name` | fix the binding |

Other refusals name the construct the same way, for example `an expression outside canonical C form (...)`.
