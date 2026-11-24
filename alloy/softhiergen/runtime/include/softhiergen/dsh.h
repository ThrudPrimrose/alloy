// softhiergen: what the generated C++ unit includes instead of <dace/dace.h>. It holds only what generated code
// refers to; it grows from compiler errors, not by guessing. No heap, no STL, no exceptions.
#ifndef DSH_H
#define DSH_H

// INFINITY and NAN, which constants print as: g++ refuses <math.h> under -ffreestanding.
#ifndef INFINITY
#define INFINITY __builtin_inff()
#endif
#ifndef NAN
#define NAN __builtin_nanf("")
#endif
#include <stddef.h>
#include <stdint.h>

#include "softhiergen/dsh_math.h"
#include "softhiergen/dsh_rt.h"
#include "softhiergen/dsh_rvv.h"

#define DACE_EXPORTED extern "C"
#define DACE_HDFI inline  // as DaCe's types.h: the index helpers come as `static DACE_HDFI constexpr`
#define DACE_DFI inline
#define __DACE_UNROLL
#define DACE_UNROLL

namespace dace {
typedef _Float16 float16;
typedef float float32;
typedef double float64;
}  // namespace dace

#endif  // DSH_H
