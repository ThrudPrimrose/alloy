# Copyright 2026 ETH Zurich and the Alloy authors.
"""A CPU reduction or scan over N elements as one program, run against a scalar reference (review R12).

The row of one register is checked on its own (:mod:`alloy.isa.validate`); an answer over several registers adds
the steps that join them: the lane-wise combine of a reduction, the carry of a scan, and on SVE the loop over blocks
under ``svwhilelt``. This module writes those steps as C, the code the answer hands out, and runs that code on
integer-valued data (every sum exact), with the extreme planted in the first, a middle, and the last lane of the
data, so a combine or a carry that skips a register, a lane, or the last block fails.
"""

import pathlib
import subprocess
import tempfile

from alloy.isa.table import Entry, Table
from alloy.isa.validate import HEADERS, arm_frame, c_compiler, c_flags, emulated, host_can_run, rvv_frame, x86_frame

__all__ = ["checked", "program"]

#: The ops this module composes, with the row that combines two registers lane-wise.
COMBINE = {"reduce_add": "add", "reduce_min": "min", "reduce_max": "max", "scan_add": "add"}
#: What a reduction's accumulator starts from on SVE, where the last block is partial.
IDENTITY = {"reduce_add": "0", "reduce_min": "INFINITY", "reduce_max": "-INFINITY"}
#: The last lane of a scanned register ``t``, broadcast to every lane: the carry into the next register.
LAST_LANE = {
    ("avx512", "f64"): "_mm512_permutexvar_pd(_mm512_set1_epi64(7), t)",
    ("avx512", "f32"): "_mm512_permutexvar_ps(_mm512_set1_epi32(15), t)",
    ("avx2", "f64"): "_mm256_permute4x64_pd(t, 0xFF)",
    ("avx2", "f32"): "_mm256_permutevar8x32_ps(t, _mm256_set1_epi32(7))",
    ("neon", "f64"): "vdupq_laneq_f64(t, 1)",
    ("neon", "f32"): "vdupq_laneq_f32(t, 3)",
    ("sve", "f64"): "svdup_n_f64(svlastb_f64(pg, t))",
    ("sve", "f32"): "svdup_n_f32(svlastb_f32(pg, t))",
}
#: Per SVE element type: the lanes of one register at run time and the all-true predicate.
SVE = {"f64": ("svcntd()", "svptrue_b64()"), "f32": ("svcntw()", "svptrue_b32()")}
TIMEOUT = 300  # seconds, qemu included


def row(entry: Entry) -> str:
    """The row as C on its signature's names (``v`` in, ``v`` or ``s`` out), one statement per line."""
    operands, _, result = entry.signature.partition("->")
    *lines, last = entry.code or (f"{entry.intrinsic}{operands.strip()}",)
    done = last if result.strip() in ("", "void") else f"{result.strip()} = {last}"
    return "".join(f"{line}; " for line in lines) + f"{done};"


def program(isa: str, op: str, dtype: str, n: int, table: Table) -> str:
    """``op`` over ``n`` elements of ``x`` as a C function ``alloy_composed``: a reduction returns its scalar, a scan
    writes ``y``. On AVX2, AVX-512 and NEON ``n`` is a whole number of registers; SVE takes any ``n``."""
    if isa == "rvv":
        return rvv_program(op, dtype, n, table)
    frame = arm_frame(isa, dtype) if isa in ("neon", "sve") else x86_frame(isa, dtype)
    t, vec = frame.scalar, frame.vector
    entry = {name: table.entry(isa, name, dtype).intrinsic for name in ("load", "store", "broadcast")}
    combine = table.entry(isa, COMBINE[op], dtype).intrinsic
    body = row(table.entry(isa, op, dtype))
    scan = op == "scan_add"
    head = (
        f"static void alloy_composed(const {t} *x, {t} *y) {{"
        if scan
        else f"static {t} alloy_composed(const {t} *x) {{"
    )
    if isa == "sve":
        count, everything = SVE[dtype]
        mask = table.entry(isa, "gen_mask", dtype).intrinsic
        loop = f"    for (int64_t i = 0; i < {n}; i += {count}) {{\n        svbool_t pg = {mask}(i, {n});\n"
        if scan:
            return (f"{head}\n    {vec} c = {entry['broadcast']}(0);\n{loop}"
                    f"        {vec} v = {entry['load']}(pg, x + i);\n        {{ {body} }}\n"
                    f"        v = {combine}(pg, v, c);\n        {{ {vec} t = v; c = {LAST_LANE[isa, dtype]}; }}\n"
                    f"        {entry['store']}(pg, y + i, v);\n    }}\n}}\n")  # fmt: skip
        kept = combine.replace("_x", "_m")  # _m keeps the accumulator's lanes the partial block masks off
        return (f"{head}\n    {vec} acc = {entry['broadcast']}({IDENTITY[op]});\n{loop}"
                f"        acc = {kept}(pg, acc, {entry['load']}(pg, x + i));\n    }}\n"
                f"    svbool_t pg = {everything};\n    {vec} v = acc;\n    {t} s;\n    {{ {body} }}\n    return s;\n}}\n")  # fmt: skip
    lanes, registers = frame.lanes, n // frame.lanes
    if scan:
        return (f"{head}\n    {vec} c = {entry['broadcast']}(0);\n    for (int k = 0; k < {registers}; k++) {{\n"
                f"        {vec} v = {entry['load']}(x + k * {lanes});\n        {{ {body} }}\n"
                f"        v = {combine}(v, c);\n        {{ {vec} t = v; c = {LAST_LANE[isa, dtype]}; }}\n"
                f"        {entry['store']}(y + k * {lanes}, v);\n    }}\n}}\n")  # fmt: skip
    return (f"{head}\n    {vec} acc = {entry['load']}(x);\n    for (int k = 1; k < {registers}; k++) "
            f"acc = {combine}(acc, {entry['load']}(x + k * {lanes}));\n"
            f"    {vec} v = acc;\n    {t} s;\n    {{ {body} }}\n    return s;\n}}\n")  # fmt: skip


def rvv_program(op: str, dtype: str, n: int, table: Table) -> str:
    """:func:`program` on RVV: passes of vl = vsetvl(n - i). A reduction folds each pass into its accumulator with the
    tail-undisturbed form (lanes past vl keep what they hold) and reduces once at VLMAX; a scan adds the scalar carry
    of the passes before, then reads the pass's last element as the next carry."""
    frame = rvv_frame("rvv", dtype)
    t, vec, suffix = frame.scalar, frame.vector, frame.suffix
    sew = 64 if dtype == "f64" else 32
    entry = {name: table.entry("rvv", name, dtype).intrinsic for name in ("load", "store", "broadcast")}
    body = row(table.entry("rvv", op, dtype))
    loop = f"    for (int64_t i = 0; i < {n};) {{\n        size_t vl = __riscv_vsetvl_e{sew}m1((size_t)({n} - i));\n"
    if op == "scan_add":
        return (f"static void alloy_composed(const {t} *x, {t} *y) {{\n    {t} c = 0;\n{loop}"
                f"        {vec} v = {entry['load']}(x + i, vl);\n        {{ {body} }}\n"
                f"        v = __riscv_vfadd_vf_{suffix}(v, c, vl);\n"
                f"        c = __riscv_vfmv_f_s_{suffix}_{dtype}(__riscv_vslidedown_vx_{suffix}(v, vl - 1, vl));\n"
                f"        {entry['store']}(y + i, v, vl);\n        i += (int64_t)vl;\n    }}\n}}\n")  # fmt: skip
    combine = table.entry("rvv", COMBINE[op], dtype).intrinsic
    return (f"static {t} alloy_composed(const {t} *x) {{\n    size_t vlmax = __riscv_vsetvlmax_e{sew}m1();\n"
            f"    {vec} acc = {entry['broadcast']}({IDENTITY[op]}, vlmax);\n{loop}"
            f"        acc = {combine}_tu(acc, acc, {entry['load']}(x + i, vl), vl);\n        i += (int64_t)vl;\n    }}\n"
            f"    size_t vl = vlmax;\n    {vec} v = acc;\n    {t} s;\n    {{ {body} }}\n    return s;\n}}\n")  # fmt: skip


#: The reference and the comparison: the extreme planted in turn at the first, a middle, and the last element.
DRIVER = """
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#define N @N@
static @T@ x[N], y[N], want[N];
int main(void) {
    long bad = 0;
    long at[3] = {0, N / 2, N - 1};
    for (int p = 0; p < 3; p++) {
        for (long i = 0; i < N; i++) x[i] = (@T@)((i * 7919) % 17 - 8);
        x[at[p]] = @EXTREME@;
@CHECK@
    }
    printf("BAD=%ld\\n", bad);
    return 0;
}
"""
REDUCE_CHECK = """        @T@ r = x[0];
        for (long i = 1; i < N; i++) r = @FOLD@;
        if (alloy_composed(x) != r) bad++;"""
SCAN_CHECK = """        @T@ r = 0;
        for (long i = 0; i < N; i++) { r += x[i]; want[i] = r; }
        alloy_composed(x, y);
        for (long i = 0; i < N; i++) if (y[i] != want[i]) bad++;"""
FOLD = {"reduce_add": "r + x[i]", "reduce_min": "fmin(r, x[i])", "reduce_max": "fmax(r, x[i])"}
EXTREME = {"reduce_add": "100", "reduce_min": "-100", "reduce_max": "100", "scan_add": "100"}


def source(isa: str, op: str, dtype: str, n: int, table: Table) -> str:
    """The whole program: the composed function and the driver that checks it."""
    scalar = "double" if dtype == "f64" else "float"
    check = SCAN_CHECK if op == "scan_add" else REDUCE_CHECK.replace("@FOLD@", FOLD.get(op, ""))
    driver = DRIVER.replace("@CHECK@", check).replace("@N@", str(n)).replace("@EXTREME@", EXTREME[op])
    return f"#include <math.h>\n#include <{HEADERS[isa]}>\n{program(isa, op, dtype, n, table)}{driver.replace('@T@', scalar)}"


def checked(isa: str, op: str, dtype: str, n: int, table: Table) -> tuple[bool | None, str]:
    """Run the composed program: (True, basis) when it matches the reference, (False, why) when it does not or does
    not build, (None, why) when this host can run neither ``isa`` nor its emulator."""
    arm = emulated(isa) if isa in ("neon", "sve", "rvv") else None
    if isa in ("neon", "sve", "rvv") and arm is None:
        return None, f"no qemu for {isa} here"
    cc = c_compiler()
    if arm is None and (cc is None or not host_can_run(isa, dtype)):
        return None, f"this host cannot run {isa}"
    compiler, flags, launcher = arm or (str(cc), tuple(c_flags(isa, dtype)), ())
    with tempfile.TemporaryDirectory(prefix="alloy_composed_") as tmp:
        folder = pathlib.Path(tmp)
        (folder / "c.c").write_text(source(isa, op, dtype, n, table))
        build = subprocess.run([compiler, "-O2", *flags, str(folder / "c.c"), "-lm", "-o", str(folder / "c")],
                               capture_output=True, text=True, check=False, timeout=TIMEOUT)  # fmt: skip
        if build.returncode != 0:
            return False, f"the {n}-element program does not build: {build.stderr.strip()[:300]}"
        run = subprocess.run([*launcher, str(folder / "c")], capture_output=True, text=True, check=False,
                             timeout=TIMEOUT)  # fmt: skip
    if not run.stdout.startswith("BAD=0"):
        return False, f"the {n}-element program differs from the scalar reference: {run.stdout.strip()[:120]}"
    where = " under qemu" if arm else ""
    return True, f"{n}-element program{where}, equal to a scalar {op}"
