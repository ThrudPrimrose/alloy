# Copyright 2026 ETH Zurich and the Alloy authors.
"""The schedule axis: which loop schedules an ISA offers, why not the rest, and ready-to-edit C
skeletons for each legal (isa, schedule, dtype) — the canonical axpy ``C[i] = a*X[i] + Y[i]`` from the
ESSENTIALS sheets, composed from the table's own entries (loads, stores, broadcast, fma, gen_mask), so
a skeleton always spells intrinsics exactly as the lookup would. This is the seed of the
schedule->vector-schedule translator (plan work item 3): emitting a different body means swapping the
axpy expression, the loop shape comes from here."""

from alloy.isa.table import ALIASES, DTYPES, Table, load
from alloy.isa.validate import TRACK_ERROR, Verdict, c_flags, compile_run, host_can_run

__all__ = ["SCHEDULES", "compiler_spelling", "legal", "skeleton", "verify"]

#: Every schedule the table knows, most conservative first.
SCHEDULES = ("scalar", "scalar_remainder", "masked_remainder", "full_mask", "sve_intrinsics")

C_TYPE = {"f64": "double", "f32": "float"}


def legal(isa: str, schedule: str, table: Table | None = None) -> str:
    """Why ``schedule`` is not offered on ``isa``, or ``""`` when it is."""
    table = table or load()
    target = table.isa(isa)
    if schedule not in table.schedule_info:
        return f"unknown schedule (one of: {', '.join(table.schedule_info)})"
    if schedule in target.schedules:
        return ""
    info = table.schedule_info[schedule]
    if schedule in ("masked_remainder", "full_mask") and not target.mask:
        return f"{isa} has no predication ({info.tail})"
    return f"{schedule} is not offered on {isa} (legal there: {', '.join(target.schedules)})"


def compiler_spelling(schedule: str, compiler: str, table: Table | None = None) -> str:
    """How to ask ``compiler`` (gcc, clang) for this schedule: flags and/or pragma. Raises KeyError
    for an unknown schedule or a compiler the table has no spelling for."""
    table = table or load()
    if schedule not in table.schedule_info:
        raise KeyError(f"{schedule!r}: unknown schedule (one of: {', '.join(table.schedule_info)})")
    info = table.schedule_info[schedule]
    spelling = {"gcc": info.gcc, "clang": info.clang}.get(compiler, "")
    if not spelling:
        raise KeyError(f"{schedule}: no {compiler!r} spelling (one of: gcc, clang)")
    return spelling


def family_of(isa: str) -> str:
    return {"avx2": "x86", "avx512": "x86"}.get(isa, isa)


def applied(template: str, mapping: dict[str, str]) -> str:
    """Apply a masked-variant template like "_mm512_maskz_loadu_pd(k, p)" to concrete arguments."""
    name, _, rest = template.partition("(")
    args = [arg.strip() for arg in rest.rstrip(")").split(",")]
    return f"{name}(" + ", ".join(mapping.get(arg, arg) for arg in args) + ")"


def fma_body(table: Table, isa: str, dtype: str, mask: str = "", pg: str = "pg") -> str:
    """The axpy vector expression ``a*X + Y`` in the target's operand order (from the table entries).
    ``mask`` is the AVX-512 opmask expression when the load and store are masked."""
    ld, bc, fm = (table.entry(isa, op, dtype) for op in ("load", "broadcast", "fma"))
    if mask and ld.masked:
        ldx = applied(ld.masked, {"k": mask, "p": "X + i"})
        ldy = applied(ld.masked, {"k": mask, "p": "Y + i"})
    else:
        ldx = f"{ld.intrinsic}(X + i)"
        ldy = f"{ld.intrinsic}(Y + i)"
    family = family_of(isa)
    if family == "x86":
        return f"{fm.intrinsic}({bc.intrinsic}(a), {ldx}, {ldy})"
    if family == "neon":
        return f"{fm.intrinsic}({ldy}, {bc.intrinsic}(a), {ldx})"
    # sve: accumulator first, everything predicated on the predicate variable
    ldx = f"{ld.intrinsic}({pg}, X + i)"
    ldy = f"{ld.intrinsic}({pg}, Y + i)"
    return f"{fm.intrinsic}({pg}, {ldy}, {bc.intrinsic}(a), {ldx})"


def store_of(table: Table, isa: str, dtype: str, value: str, mask: str = "", pg: str = "pg") -> str:
    st = table.entry(isa, "store", dtype)
    if mask and st.masked:
        return f"{applied(st.masked, {'p': 'C + i', 'k': mask, 'v': value})};"
    if family_of(isa) == "sve":
        return f"{st.intrinsic}({pg}, C + i, {value});"
    return f"{st.intrinsic}(C + i, {value});"


def lanes_of(table: Table, isa: str, dtype: str) -> tuple[int, str]:
    """Static lanes and the C step expression for a schedule's loop."""
    target = table.isa(isa)
    if family_of(isa) == "sve":
        return target.lanes[dtype] or 0, "svcntd()" if dtype == "f64" else "svcntw()"
    return target.lanes[dtype], str(target.lanes[dtype])


def scalar_loop(bound: str) -> str:
    return f"for (int64_t i = 0; i < {bound}; i++) {{\n    C[i] = a * X[i] + Y[i];\n}}"


def skeleton(table: Table, isa: str, schedule: str, dtype: str) -> str:
    """The canonical axpy C source for a legal (isa, schedule, dtype), or ``KeyError`` naming why the
    combination is not offered."""
    if dtype not in DTYPES:
        raise KeyError(f"{isa}/{dtype}: skeletons exist for the float dtypes ({', '.join(DTYPES)})")
    if isa in ALIASES:
        raise KeyError(f"{isa}: a compiler width knob with no intrinsics of its own: use {ALIASES[isa]}")
    why = legal(isa, schedule, table)
    if why:
        raise KeyError(f"{isa}/{schedule}/{dtype}: {why}")
    family = family_of(isa)
    s = C_TYPE[dtype]
    lanes, step = lanes_of(table, isa, dtype)
    header = {"x86": "#include <immintrin.h>", "neon": "#include <arm_neon.h>", "sve": "#include <arm_sve.h>"}[family]
    body = sve_body(table, dtype, schedule, step) if family == "sve" else simd_body(table, isa, dtype, schedule, lanes)
    return (
        f"{header}\n#include <stdint.h>\n\n"
        f"/* {isa}/{dtype}, schedule '{schedule}': {table.schedule_info[schedule].description} */\n"
        f"/* build: {' '.join(c_flags(isa, dtype)) or 'no target flag'} */\n"
        f"void axpy(int64_t N, {s} a, const {s} *X, const {s} *Y, {s} *C) {{\n"
        f"{body}\n}}"
    )


def mask_setup(table: Table, isa: str, dtype: str, lanes: int, left: str) -> tuple[str, str]:
    """The iota vector and the mask of the first ``left`` lanes."""
    bits = "64" if dtype == "f64" else "32"
    cmplt = table.entry(isa, "gen_mask", dtype).intrinsic
    iota = f"const __m512i iota = _mm512_setr_epi{bits}(" + ", ".join(str(j) for j in range(lanes)) + ");"
    return iota, f"__mmask{lanes} m = {cmplt}(iota, _mm512_set1_epi{bits}({left}));"


def simd_body(table: Table, isa: str, dtype: str, schedule: str, lanes: int) -> str:
    """The loop of a fixed-width ISA."""
    if schedule == "scalar":
        return scalar_loop("N")
    masked = store_of(table, isa, dtype, fma_body(table, isa, dtype, mask="m"), mask="m") if table.isa(isa).mask else ""
    main = store_of(table, isa, dtype, fma_body(table, isa, dtype))
    if schedule == "scalar_remainder":
        return (
            f"const int64_t n_main = {lanes} * (N / {lanes});\n"
            f"for (int64_t i = 0; i < n_main; i += {lanes}) {{\n"
            f"    {main}\n"
            f"}}\n"
            f"for (int64_t i = n_main; i < N; i++) {{\n"
            f"    C[i] = a * X[i] + Y[i];\n"
            f"}}"
        )
    if schedule == "masked_remainder":
        iota, mask = mask_setup(table, isa, dtype, lanes, "N - i")
        return (
            f"{iota}\n"
            f"int64_t i = 0;\n"
            f"for (; i + {lanes} <= N; i += {lanes}) {{\n"
            f"    {main}\n"
            f"}}\n"
            f"if (i < N) {{\n"
            f"    {mask}\n"
            f"    {masked}\n"
            f"}}"
        )
    iota, mask = mask_setup(table, isa, dtype, lanes, f"N - i < {lanes} ? N - i : {lanes}")  # a 32-bit lane truncates
    return f"{iota}\nfor (int64_t i = 0; i < N; i += {lanes}) {{\n    {mask}\n    {masked}\n}}"


def sve_body(table: Table, dtype: str, schedule: str, step: str) -> str:
    """The loop of SVE: signed, so a negative N runs no iteration, as every other skeleton."""
    if schedule == "scalar":
        return scalar_loop("N")
    gen = table.entry("sve", "gen_mask", dtype).intrinsic
    every = "svptrue_b64()" if dtype == "f64" else "svptrue_b32()"
    tail = store_of(table, "sve", dtype, fma_body(table, "sve", dtype, pg="__pg_i"), pg="__pg_i")
    main = store_of(table, "sve", dtype, fma_body(table, "sve", dtype, pg="pg"), pg="pg")
    if schedule in ("sve_intrinsics", "full_mask"):
        return f"for (int64_t i = 0; i < N; i += {step}) {{\n    svbool_t __pg_i = {gen}(i, N);\n    {tail}\n}}"
    head = (
        f"const int64_t vl = {step};\n"
        f"const svbool_t pg = {every};\n"
        f"int64_t i = 0;\n"
        f"for (; i + vl <= N; i += vl) {{\n"
        f"    {main}\n"
        f"}}\n"
    )
    if schedule == "scalar_remainder":
        return f"{head}for (; i < N; i++) {{\n    C[i] = a * X[i] + Y[i];\n}}"
    return f"{head}if (i < N) {{\n    svbool_t __pg_i = {gen}(i, N);\n    {tail}\n}}"


DRIVER = """
#include <stdio.h>
#include <math.h>
int main(void) {{
  enum {{ MAX_N = 67 }};
  {ctype} a = 1.5{fsuffix}, X[MAX_N + 1], Y[MAX_N + 1], C[MAX_N + 1];
  double maxrel = 0;
  for (int i = 0; i <= MAX_N; i++) {{ X[i] = 1; Y[i] = 1; C[i] = -7; }}
  axpy(-1, a, X, Y, C);
  for (int i = 0; i <= MAX_N; i++) if (C[i] != -7) maxrel = 1;  /* a negative extent runs nothing */
  for (int N = 0; N <= MAX_N; N++) {{
    for (int i = 0; i <= MAX_N; i++) {{ X[i] = ({ctype})(0.5 + 0.1 * i); Y[i] = ({ctype})(1.0 + 0.25 * i); C[i] = -7; }}
    axpy(N, a, X, Y, C);
    for (int i = 0; i <= MAX_N; i++) {{
      double ref = i < N ? (double)a * (double)X[i] + (double)Y[i] : -7;  /* past N must stay untouched */
      double d = fabs((double)C[i] - ref);
      double m = fabs(ref) > 1 ? fabs(ref) : 1;
      {track}
    }}
  }}
  printf("ALLOY-VERIFY rel=%.6e\\n", maxrel);
  return 0;
}}"""

#: Skeleton tolerance per lane type: fma rounds once, the reference twice.
SKELETON_TOL = {"f64": 1e-14, "f32": 1e-6}


def verify(isa: str, schedule: str, dtype: str, table: Table | None = None) -> Verdict:
    """Compile and run a skeleton against the scalar reference: the same numerical gate as for table
    entries, applied to the composed loop shape. ``ok is None`` when this host cannot execute it."""
    table = table or load()
    why = legal(isa, schedule, table)
    if why:
        raise KeyError(f"{isa}/{schedule}/{dtype}: {why}")
    if not host_can_run(isa, dtype):
        return Verdict(None, f"host cannot execute {isa}/{dtype} kernels (unverified, not wrong)")
    ctype = C_TYPE[dtype]
    fsuffix = "" if dtype == "f64" else "f"
    source = skeleton(table, isa, schedule, dtype) + DRIVER.format(ctype=ctype, fsuffix=fsuffix, track=TRACK_ERROR)
    try:
        rel = compile_run(source, c_flags(isa, dtype))
    except RuntimeError as exc:
        return Verdict(False, "compiled skeleton", str(exc))
    tol = SKELETON_TOL[dtype]
    ok = rel <= tol
    return Verdict(ok, "compiled skeleton", f"max rel err {rel:.3e} vs tolerance {tol:.3e}")
