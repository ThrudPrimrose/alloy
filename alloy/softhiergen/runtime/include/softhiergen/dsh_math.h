// dace-softhier: Python's // and %, which DaCe prints for the element addresses of a placed array.
#ifndef DSH_MATH_H
#define DSH_MATH_H

static inline int py_floor(int a, int b) { return a / b - (a % b != 0 && (a < 0) != (b < 0)); }
static inline int py_mod(int a, int b) {
    int r = a % b;
    return r != 0 && (r < 0) != (b < 0) ? r + b : r;
}

#endif  // DSH_MATH_H
