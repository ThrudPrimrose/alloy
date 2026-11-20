# Copyright 2026 ETH Zurich and the Alloy authors.
"""The SoftHier v1 rows (``softhier.toml``) and their verdicts (``softhier_verified.toml``).

A SoftHier row is C that a kernel on the GVSoC model ``pulp.chips.soft_hier_old.flex_cluster`` calls: an RVV loop on
the Spatz vector unit, an iDMA copy and its wait, a RedMulE product and its wait, or a barrier. Rows are verified by
running them on GVSoC (``softhier_harness.py``); ``python -m alloy.isa.softhier verify`` does that where the simulator
is installed, and ``record`` turns the harness's output from another machine into the verdict file.

    python -m alloy.isa.softhier arch                  # the v1 architecture file (SOFTHIER_ARCH_FILE)
    python -m alloy.isa.softhier rows > rows.json      # the harness input, planted rows included
    python -m alloy.isa.softhier verify --image softhier-v1.sif   # run the harness in the image (helpers/build_softhier*)
    python -m alloy.isa.softhier verify                # or here, with SOFTHIER_SDK and SOFTHIER_GVSOC set
    python -m alloy.isa.softhier record out.txt --image softhier-v1.sif   # verdicts from a run elsewhere
"""

import argparse
import dataclasses
import datetime
import functools
import hashlib
import json
import os
import pathlib
import shutil
import string
import subprocess
import sys
import tempfile
import tomllib

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from alloy.isa import softhier_harness
from alloy.jsontype import Json

__all__ = ["ROWS_PATH", "Row", "Verdict", "build_line", "code", "digest", "rows", "verdicts"]

HERE = pathlib.Path(__file__).parent
ROWS_PATH = HERE / "softhier.toml"
VERDICTS_PATH = HERE / "softhier_verified.toml"
HARNESS = HERE / "softhier_harness.py"
#: The pinned sources (softhier_pins.toml): the verdict file records them, and a record of other pins is stale.
PINS_PATH = HERE / "softhier_pins.toml"
TARGET = "pulp.chips.soft_hier_old.flex_cluster"
#: Writes the v1 flex_cluster_arch.h over the SDK's own: its headers include it by quotes, so the compiler takes the
#: copy beside them before any -I folder (a header of another configuration breaks the barriers without an error).
ARCH_HEADER = (
    "python -m alloy.isa.softhier arch > alloy_v1.py; python $SOFTHIER_SDK/utilities/config.py alloy_v1.py "
    "--output-dir $SOFTHIER_SDK/runtime/runtime/include"
)
#: The SDK's compile flags (runtime/CMakeLists.txt) with zvfh added, so f16 vector intrinsics compile.
FLAGS = ["-mabi=ilp32d", "-mcmodel=medlow", "-march=rv32imafdv_zfh_zvfh", "-O3", "-ffast-math", "-fno-builtin",
         "-fno-tree-vectorize", "-fno-common", "-ffunction-sections"]  # fmt: skip
#: Per kind and element type: the largest max |out - ref| / max |ref| a run may show. Elementwise: one rounding (2u).
#: reduce_add: one rounding per strip of a sum whose last strip holds the largest terms (5 strips of f32, 3 of f16, a
#: few u), so dropping the tail or five terms is outside it. reduce_max is exact. mma: the model rounds an f32 sum to
#: f16 once (2u, about 4.5x the 2.2e-4 measured on 2026-11-18).
TOLERANCE = {"f32": 1e-6, "f16": 1e-3, "reduction_f32": 1e-6, "reduction_f16": 2e-3, "mma_f16": 1e-3}
C_TYPES = {"f32": "float", "f16": "_Float16"}
#: Wrong rows the harness must fail: a row's name, and the text in its code swapped for the wrong one.
PLANTED = {
    "planted_add_is_sub": ("add", "__riscv_vfadd_vv_", "__riscv_vfsub_vv_"),
    "planted_copy_2d_strides_swapped": (
        "copy_2d", "flex_dma_async_2d(dst, src, row_bytes, dst_stride, src_stride, rows)",
        "flex_dma_async_2d(dst, src, row_bytes, src_stride, dst_stride, rows)",
    ),
    "planted_barrier_global_removed": ("barrier_global", "flex_global_barrier_xy();", ";"),
    "planted_reduce_add_without_tail": ("reduce_add", "i < n;", "i + __riscv_vsetvlmax_e${b}m8() <= n;"),
    "planted_reduce_max_without_tail": ("reduce_max", "i < n;", "i + __riscv_vsetvlmax_e${b}m8() <= n;"),
}  # fmt: skip
RUN_TIMEOUT = 3600


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Row:
    """One way to do ``op`` on SoftHier: its unit (spatz, idma, redmule, cluster), the ``kind`` of program that checks
    it, the element types it was run at, the call it makes, and its ``code`` (``$t``, ``$b``, ``$s`` stand for the C
    type, its bits, and its RVV suffix). ``name`` tells apart rows of one op."""

    op: str
    unit: str
    kind: str
    dtypes: tuple[str, ...]
    call: str
    code: str
    name: str = ""
    note: str = ""
    #: A wait runs inside the program of the row that issues its work, whose code holds the wait's code.
    checked_by: str = ""

    def key(self) -> str:
        return self.name or self.op


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Verdict:
    """One row's run at one element type; ``digest`` is :func:`digest` of the row as it ran."""

    name: str
    dtype: str
    ok: bool
    rel: float | None
    error: str = ""
    digest: str = ""


@functools.lru_cache(maxsize=None, typed=True)
def table(path: pathlib.Path = ROWS_PATH) -> Json:
    return tomllib.loads(path.read_text())


def rows() -> tuple[Row, ...]:
    return tuple(Row(op=op, **row) for op, entries in table()["ops"].items() for row in entries)


def untyped(row: Row) -> bool:
    """A row that moves bytes or no data (a copy, its wait, a barrier): it answers at any element type."""
    return set(row.dtypes) <= {"bytes", "none"}


def config() -> Json:
    configured: Json = table()["target"]["config"]
    return configured


def vlmax(dtype: str) -> int:
    """Elements of one LMUL-8 register group: VLEN * 8 / SEW, VLEN = VLSU ports x port width."""
    vlen: int = config()["spatz_num_vlsu_port"] * config()["spatz_vlsu_port_width"]
    return vlen * 8 // int(dtype[1:])


def spelled(text: str, dtype: str) -> str:
    """``text`` with ``$t``, ``$b``, ``$s`` filled for ``dtype`` (a non-vector row has none)."""
    if dtype not in C_TYPES:
        return text
    return string.Template(text).substitute(t=C_TYPES[dtype], b=dtype[1:], s=dtype)


def code(row: Row, dtype: str) -> str:
    return spelled(row.code, dtype).strip() + "\n"


def function(row: Row, dtype: str) -> str:
    """The function of ``row``'s code the check calls by name (vector and barrier rows)."""
    return f"alloy_{row.op}_{dtype}" if dtype in C_TYPES else f"alloy_{row.key()}"


def tolerance(row: Row, dtype: str) -> float:
    if row.op == "reduce_max":
        return 0.0
    if row.kind in ("reduction", "mma"):
        return TOLERANCE[f"{row.kind}_{dtype}"]
    return TOLERANCE.get(dtype, 0.0)


def arch() -> str:
    """The v1 configuration as the simulator's architecture file, the form of the SDK's examples/SoftHier/config."""
    return softhier_harness.arch_file(config())


def build_line() -> str:
    """The line that compiles an answer's code, saved as alloy.c, once :data:`ARCH_HEADER` has written the v1
    flex_cluster_arch.h into the SDK's include folder."""
    return " ".join(["riscv32-unknown-elf-gcc", *FLAGS, "-I", "$SOFTHIER_SDK/runtime/runtime/include", "-c", "alloy.c",
                     "-o", "alloy.o"])  # fmt: skip


def link_line() -> str:
    """The line that builds the program: the SDK headers define their functions (not static), so the kernel and main
    share one file, program.c."""
    sdk = "$SOFTHIER_SDK/runtime/runtime"
    return " ".join(["riscv32-unknown-elf-gcc", "-I", f"{sdk}/include", "-T", f"{sdk}/flex_memory.ld",
                     "-nostartfiles", *FLAGS, "-Wl,--gc-sections", "-o", "softhier.elf", f"{sdk}/flex_start.s",
                     "program.c"])  # fmt: skip


def run_line() -> str:
    return f"SOFTHIER_ARCH_FILE=alloy_v1.py gvsoc --target={TARGET} --binary softhier.elf run"


def pins() -> dict[str, str]:
    """softhier_pins.toml as the verdict file records it: one line per source."""
    found = tomllib.loads(PINS_PATH.read_text())
    gvsoc = found["gvsoc"]
    submodules = ", ".join(f"{name} {commit}" for name, commit in gvsoc["submodules"].items())
    return {
        "base": found["base"]["image"],
        "gvsoc": f"{gvsoc['url']} {gvsoc['commit']} ({submodules})",
        "sdk": f"{found['sdk']['url']} {found['sdk']['commit']}",
        "toolchain": f"{found['toolchain']['url']} sha256:{found['toolchain']['sha256']}",
        "systemc": f"{found['systemc']['url']} {found['systemc']['commit']}",
        "dramsys": f"{found['dramsys']['url']} {found['dramsys']['commit']}",
        "pins": "sha256:" + hashlib.sha256(PINS_PATH.read_bytes()).hexdigest(),  # what DRAMSys fetches, Python, uv
    }


def digest(row: Row, dtype: str) -> str:
    """What a run of ``row`` at ``dtype`` checked: its code and the code of the waits its program runs, kind, unit,
    the configuration, the flags, the bound, and the harness that drew the inputs and compared the results."""
    waits = [code(w, dtype) for w in rows() if w.checked_by == row.key()]
    harness = hashlib.sha256(HARNESS.read_bytes()).hexdigest()
    checked = [code(row, dtype), waits, row.kind, row.unit, dtype, config(), FLAGS, tolerance(row, dtype), harness]
    return hashlib.sha256(json.dumps(checked).encode()).hexdigest()[:16]


@functools.lru_cache(maxsize=None, typed=True)
def recorded(path: pathlib.Path = VERDICTS_PATH) -> Json:
    return tomllib.loads(path.read_text()) if path.is_file() else {}


def verdicts(path: pathlib.Path = VERDICTS_PATH) -> dict[tuple[str, str], Verdict]:
    """``(name, dtype)`` -> the recorded verdict of that row as it is now: a record of a row changed since its run, or
    a record made on other pins, is stale and left out, so the row is unverified until it runs again."""
    record = recorded(path)
    if any(record.get(key) != value for key, value in pins().items()):
        return {}
    current = {(r.key(), d): digest(r, d) for r in rows() for d in r.dtypes}
    found = (Verdict(**v) for v in record.get("verdicts", []))
    return {(v.name, v.dtype): v for v in found if current.get((v.name, v.dtype)) == v.digest}


def verdict_of(row: Row, dtype: str) -> Verdict | None:
    """``row``'s current verdict at ``dtype``: a wait's is the verdict of the row whose program runs it."""
    return verdicts().get((row.checked_by or row.key(), dtype))


def planted() -> tuple[Row, ...]:
    """The wrong rows: real rows with one call changed, which their check must fail."""
    by_key = {r.key(): r for r in rows()}
    found = []
    for name, (real, right, wrong) in PLANTED.items():
        row = by_key[real]
        assert right in row.code, (name, right)
        found.append(dataclasses.replace(row, name=name, code=row.code.replace(right, wrong)))
    return tuple(found)


def harness_rows(with_planted: bool = True) -> list[Json]:
    """Every row at every element type it runs at, as the harness reads them."""
    chosen = tuple(r for r in rows() if not r.checked_by) + (planted() if with_planted else ())
    by_key = {r.key(): r for r in rows()}
    real = {
        r.key(): by_key[PLANTED[r.key()][0]] if r.key() in PLANTED else r for r in chosen
    }  # whose function it calls
    return [
        {"name": r.key(), "op": r.op, "dtype": d, "kind": r.kind, "unit": r.unit, "code": code(r, d),
         "fn": function(real[r.key()], d), "tol": tolerance(r, d)}
        for r in chosen
        for d in r.dtypes
    ]  # fmt: skip


def spec(jobs: int = 8, scratch: str | None = None) -> Json:
    """The harness's input: the configuration, the build, link, and run lines as argument lists, and the rows."""
    compile_ = ["riscv32-unknown-elf-gcc", *FLAGS, "-I", "{sdk}/runtime/runtime/include", "-c", "alloy.c", "-o",
                "alloy.o"]  # fmt: skip
    link = ["riscv32-unknown-elf-gcc", "-I", "{sdk}/runtime/runtime/include", "-T",
            "{sdk}/runtime/runtime/flex_memory.ld", "-nostartfiles", *FLAGS, "-Wl,--gc-sections", "-o", "softhier.elf",
            "{sdk}/runtime/runtime/flex_start.s"]  # fmt: skip
    run = [f"--target={TARGET}", "--binary", "softhier.elf", "run"]
    return {"arch": arch(), "compile": compile_, "link": link, "run": run, "rows": harness_rows(), "jobs": jobs,
            "scratch": scratch}  # fmt: skip


def parsed(output: str) -> tuple[list[Verdict], list[Verdict]]:
    """The harness's printed verdicts, digested, split into the table's rows and the planted ones."""
    by_key = {r.key(): r for r in rows() + planted()}
    found = [Verdict(**json.loads(line.split(" ", 1)[1])) for line in output.splitlines()
             if line.startswith("SOFTHIER-VERDICT ")]  # fmt: skip
    found = [dataclasses.replace(v, digest=digest(by_key[v.name], v.dtype)) for v in found]
    return [v for v in found if v.name not in PLANTED], [v for v in found if v.name in PLANTED]


def verdicts_text(found: list[Verdict], wrong: list[Verdict], run: str, image: str = "") -> str:
    head = [
        "# Written by `python -m alloy.isa.softhier record` (or verify): every softhier.toml row run on GVSoC (simulated",
        "# SoftHier v1). [[planted]] are rows with one call changed on purpose (softhier.PLANTED): their runs must fail.",
        f'run = "{run}"',
        *(f"{key} = {json.dumps(value)}" for key, value in pins().items()),
        f'target = "{TARGET}"',
        *([f'image = "{image}"'] if image else []),
        "",
    ]
    body = []
    for section, verdicts_ in (("verdicts", found), ("planted", wrong)):
        for v in verdicts_:
            fields = {"name": v.name, "dtype": v.dtype, "ok": v.ok, "rel": v.rel, "error": v.error or None,
                      "digest": v.digest or None}  # fmt: skip
            body += [f"[[{section}]]", *(f"{k} = {json.dumps(x)}" for k, x in fields.items() if x is not None), ""]
    return "\n".join(head + body)


def record(output: str, image: str = "") -> tuple[list[Verdict], list[Verdict]]:
    """The harness's output written as :data:`VERDICTS_PATH`; every row and planted row must have a verdict."""
    found, wrong = parsed(output)
    expected = len(harness_rows())  # waits run inside their issuers' programs
    if len(found) + len(wrong) != expected:
        raise RuntimeError(f"the harness gave {len(found) + len(wrong)} of {expected} verdicts")
    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    VERDICTS_PATH.write_text(verdicts_text(found, wrong, today, image))
    recorded.cache_clear()
    return found, wrong


def image_digest(image: pathlib.Path) -> str:
    """``sha256:<hex>`` of an image file, as the verdict file records it."""
    with image.open("rb") as stream:  # in chunks: an image holds gigabytes
        return "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()


def run_harness(jobs: int = 8, image: pathlib.Path | None = None) -> str:
    """The harness over every row: inside ``image`` (the SoftHier v1 Apptainer image, which sets SOFTHIER_SDK and
    SOFTHIER_GVSOC), or on the GVSoC those variables name here. Its printed output."""
    if image is None:
        for name in ("SOFTHIER_SDK", "SOFTHIER_GVSOC"):
            if name not in os.environ:
                raise RuntimeError(f"{name} is not set: the harness builds with the SDK and runs on GVSoC")
    with tempfile.TemporaryDirectory(prefix="alloy_softhier_") as tmp:
        work = pathlib.Path(tmp)
        (work / "rows.json").write_text(json.dumps(spec(jobs, tmp)))
        shutil.copy(HARNESS, work / "softhier_harness.py")
        command = [sys.executable, str(work / "softhier_harness.py"), str(work / "rows.json")]
        if image is not None:
            command = ["singularity", "exec", "-B", tmp, str(image), "python3", *command[1:]]
        done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=RUN_TIMEOUT)
    if done.returncode != 0:
        raise RuntimeError(f"the harness exited {done.returncode}: {done.stderr[-1500:]}")
    return done.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.isa.softhier", description=__doc__)
    parser.add_argument("command", choices=("arch", "rows", "verify", "record"))
    parser.add_argument("output", nargs="?", type=pathlib.Path, help="record: the harness's printed output")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--image", type=pathlib.Path, help="verify: run inside this image; both: record its digest")
    args = parser.parse_args(argv)
    if args.command == "arch":
        print(arch(), end="")
        return 0
    if args.command == "rows":
        print(json.dumps(spec(args.jobs)))
        return 0
    text = args.output.read_text() if args.command == "record" else run_harness(args.jobs, args.image)
    found, wrong = record(text, image_digest(args.image) if args.image else "")
    for v in found + wrong:
        state = "ok" if v.ok else "FAIL"
        print(f"{v.name:32} {v.dtype:5} {state} {v.rel if v.rel is not None else ''} {v.error[:120]}")
    return 1 if any(not v.ok for v in found) or any(v.ok for v in wrong) else 0


if __name__ == "__main__":
    sys.exit(main())
