# Copyright 2026 ETH Zurich and the Alloy authors.
"""Runs SoftHier table rows on GVSoC and prints one JSON verdict per row. Standalone: it runs next to the simulator
(Python 3, the standard library only) and never imports alloy; alloy's tests read the programs it renders.

    python3 softhier_harness.py rows.json   # {"arch", "compile", "link", "run", "rows": [{"name", "dtype", ...}]}

Each row runs as one program built with the SDK and the GCC 14 RISC-V toolchain: the row's code (as the lookup
answers it, also compiled alone with the answer's build line), then a driver that puts deterministic inputs into
cluster 0's TCDM, calls the row's functions, and prints every result word as ``ALLOY <hex>``. The harness compares the
words with a float64 (or exact) reference: ``rel`` is max |out - ref| / max |ref|.

Environment: ``SOFTHIER_SDK`` (the softhier-sdk checkout), ``SOFTHIER_GVSOC`` (the GVSoC checkout with
``install/bin/gvsoc``), the toolchain's ``bin`` on PATH, and the DRAMSys and SystemC libraries on LD_LIBRARY_PATH."""

import concurrent.futures
import json
import os
import pathlib
import random
import struct
import subprocess
import sys
import tempfile

#: Elements of a vector row's operands: several strips of e32m8 and e16m8 at VLEN 256 (64 and 128 elements) and a tail.
VECTOR_N = 300
#: Words of the 1D copy.
DMA_WORDS = 1000
#: The 2D copy: a block of BLOCK rows x cols at (ROW0, COL0) of a ROWS x COLS matrix of 32-bit words.
ROWS, COLS, ROW0, COL0, BLOCK = 16, 24, 3, 5, (8, 10)
#: The matrix product c (M x N) += a (M x K) b (K x N), extents that are no multiple of RedMulE's 32 x 128 array.
MMA = (24, 72, 40)
#: TCDM offsets of the driver's buffers (the TCDM of v1 holds 1 MiB at local address 0).
TCDM = (0x1000, 0x20000, 0x40000, 0x60000)
#: HBM offsets on west node 0.
HBM = (0x1000, 0x100000)
#: Inputs per op: the interval values are drawn from.
DOMAIN = {"reduce_add": (0.5, 1.0), "mma": (-1.0, 1.0)}
CTYPE = {"f32": "float", "f16": "_Float16"}
WORD = {"f32": ("I", "f", 32), "f16": ("H", "e", 16)}


def rounded(value: float, dtype: str) -> float:
    """``value`` rounded to ``dtype``."""
    code = WORD[dtype][1]
    return float(struct.unpack(code, struct.pack(code, value))[0])


def bits(value: float, dtype: str) -> int:
    word, code, _ = WORD[dtype]
    return int(struct.unpack(word, struct.pack(code, value))[0])


def value(word: int, dtype: str) -> float:
    unsigned, code, _ = WORD[dtype]
    return float(struct.unpack(code, struct.pack(unsigned, word))[0])


def draw(op: str, dtype: str, count: int, seed: int) -> list[float]:
    low, high = DOMAIN.get(op, (-4.0, 4.0))
    generator = random.Random(seed)
    return [rounded(generator.uniform(low, high), dtype) for _ in range(count)]


def c_array(name: str, words: list[int], width: int) -> str:
    """A constant array of ``words`` (bit patterns) in the program's read-only data."""
    body = ", ".join(f"0x{w:x}" for w in words)
    return f"static const uint{width}_t {name}[{len(words)}] = {{{body}}};\n"


def fill(name: str, offset: int, width: int, count: int) -> str:
    """Core 0 copies the constant array ``name`` into TCDM at ``offset``."""
    return f"        for (int i = 0; i < {count}; ++i) ((volatile uint{width}_t*)local(0x{offset:x}))[i] = {name}[i];\n"


def dump(offset: int, width: int, count: int) -> str:
    """Core 0 prints ``count`` words of TCDM at ``offset``."""
    return (
        f"        for (int i = 0; i < {count}; ++i) "
        f'printf("ALLOY %x\\n", (uint32_t)((volatile uint{width}_t*)local(0x{offset:x}))[i]);\n'
    )


def program(row: dict) -> tuple[str, list[int]]:
    """The test program of ``row``, its code first, and the result words it must print, in order."""
    kind, op, dtype, name = row["kind"], row["op"], row["dtype"], row["name"]
    data, body = "", ""
    if kind in ("binary", "fma", "move", "reduction"):
        width = WORD[dtype][2]
        arity = {"binary": 2, "fma": 3, "move": 1, "reduction": 1}[kind]
        inputs = [draw(op, dtype, VECTOR_N, seed) for seed in range(arity)]
        for i, xs in enumerate(inputs):
            data += c_array(f"IN{i}", [bits(x, dtype) for x in xs], width)
        t = CTYPE[dtype]
        pointers = ", ".join(f"(const {t}*)local(0x{TCDM[i + 1]:x})" for i in range(arity))
        fills = "".join(fill(f"IN{i}", TCDM[i + 1], width, VECTOR_N) for i in range(arity))
        if kind == "reduction":
            call = (
                f"        volatile {t} r = {row['fn']}({pointers}, {VECTOR_N});\n"
                f'        printf("ALLOY %x\\n", (uint32_t)*(volatile uint{width}_t*)&r);\n'
            )
        else:
            call = f"        {row['fn']}(({t}*)local(0x{TCDM[0]:x}), {pointers}, {VECTOR_N});\n" + dump(
                TCDM[0], width, VECTOR_N
            )
        body = f"    if (flex_get_core_id() == 0) {{  // the Spatz core\n{fills}{call}    }}\n"
        body = f"    if (flex_get_cluster_id() == 0) {{\n{body}    }}\n"
        return frame(row["code"], data, body), []  # compared with reference()
    if kind == "dma_1d":
        words = [random.Random(7).getrandbits(32) for _ in range(DMA_WORDS)]
        data = c_array("IN0", words, 32)
        nbytes = DMA_WORDS * 4
        body = (
            f"    if (flex_get_core_id() == 0) {{\n{fill('IN0', TCDM[0], 32, DMA_WORDS)}    }}\n"
            "    flex_intra_cluster_sync();\n"
            f"    alloy_copy_1d(hbm_west(0, 0x{HBM[0]:x}), local(0x{TCDM[0]:x}), {nbytes});  // TCDM to HBM\n"
            "    alloy_wait_idma();\n"
            f"    alloy_copy_1d(local(0x{TCDM[1]:x}), hbm_west(0, 0x{HBM[0]:x}), {nbytes});  // HBM to TCDM\n"
            "    alloy_wait_idma();\n"
            f"    if (flex_get_core_id() == 0) {{\n{dump(TCDM[1], 32, DMA_WORDS)}    }}\n"
        )
        return frame(row["code"], data, cluster0(body)), words
    if kind == "dma_2d":
        words = [random.Random(8).getrandbits(32) for _ in range(ROWS * COLS)]
        rows, cols = BLOCK
        block = [words[(ROW0 + r) * COLS + COL0 + c] for r in range(rows) for c in range(cols)]
        scattered = [0] * (ROWS * COLS)
        for r in range(rows):
            for c in range(cols):
                scattered[(ROW0 + r) * COLS + COL0 + c] = block[r * cols + c]
        data = c_array("IN0", words, 32)
        nbytes, corner = ROWS * COLS * 4, (ROW0 * COLS + COL0) * 4
        body = (
            f"    if (flex_get_core_id() == 0) {{\n{fill('IN0', TCDM[0], 32, ROWS * COLS)}"
            f"        for (int i = 0; i < {ROWS * COLS}; ++i) ((volatile uint32_t*)local(0x{TCDM[3]:x}))[i] = 0;\n    }}\n"
            "    flex_intra_cluster_sync();\n"
            f"    alloy_copy_1d(hbm_west(0, 0x{HBM[0]:x}), local(0x{TCDM[0]:x}), {nbytes});  // the matrix to HBM\n"
            f"    alloy_copy_1d(hbm_west(0, 0x{HBM[1]:x}), local(0x{TCDM[3]:x}), {nbytes});  // zeros to HBM\n"
            "    alloy_wait_idma();\n"
            f"    alloy_copy_2d(local(0x{TCDM[1]:x}), hbm_west(0, 0x{HBM[0]:x} + {corner}), {cols * 4}, {cols * 4}, "
            f"{COLS * 4}, {rows});  // gather the block: HBM to TCDM\n"
            "    alloy_wait_idma();\n"
            f"    alloy_copy_2d(hbm_west(0, 0x{HBM[1]:x} + {corner}), local(0x{TCDM[1]:x}), {cols * 4}, {COLS * 4}, "
            f"{cols * 4}, {rows});  // scatter it back: TCDM to HBM\n"
            "    alloy_wait_idma();\n"
            f"    alloy_copy_1d(local(0x{TCDM[2]:x}), hbm_west(0, 0x{HBM[1]:x}), {nbytes});\n"
            "    alloy_wait_idma();\n"
            f"    if (flex_get_core_id() == 0) {{\n{dump(TCDM[1], 32, rows * cols)}{dump(TCDM[2], 32, ROWS * COLS)}    }}\n"
        )
        return frame(row["code"], data, cluster0(body)), block + scattered
    if kind == "mma":
        m, n, k = MMA
        operands = [draw("mma", "f16", count, seed) for seed, count in enumerate((m * k, k * n, m * n))]
        for i, xs in enumerate(operands):
            data += c_array(f"IN{i}", [bits(x, "f16") for x in xs], 16)
        fills = "".join(fill(f"IN{i}", TCDM[i], 16, len(xs)) for i, xs in enumerate(operands))
        body = (
            f"    if (flex_get_core_id() == 0) {{\n{fills}    }}\n"
            "    flex_intra_cluster_sync();\n"
            f"    alloy_mma_f16(0x{TCDM[0]:x}, 0x{TCDM[1]:x}, 0x{TCDM[2]:x}, {m}, {n}, {k});\n"
            "    alloy_wait_redmule();\n"
            f"    if (flex_get_core_id() == 0) {{\n{dump(TCDM[2], 16, m * n)}    }}\n"
        )
        return frame(row["code"], data, cluster0(body)), []
    if kind == "sync_cluster":
        # core i waits longer the higher its id, then writes i + 1 into slot i; core 0 reads every slot after the sync
        body = (
            "    uint32_t id = flex_get_core_id();\n"
            "    for (volatile uint32_t spin = 0; spin < 400 * id; ++spin) {}\n"
            f"    ((volatile uint32_t*)local(0x{TCDM[0]:x}))[id] = id + 1;\n"
            f"    {row['fn']}();\n"
            f"    if (id == 0) {{\n{dump(TCDM[0], 32, 3)}    }}\n"
        )
        return frame(row["code"], data, cluster0(body)), [1, 2, 3]
    if kind == "barrier_global":
        # core 0 of cluster c waits longer the higher c is, then writes c + 1 into its own TCDM; after the barrier,
        # cluster 0's DMA core reads every cluster's word (cores reach other clusters' TCDM only through iDMA)
        clusters = 4
        reads = "".join(
            f"        flex_dma_async_1d(local(0x{TCDM[1]:x} + {4 * c}), remote_cid({c}, 0x{TCDM[0]:x}), 4);\n"
            for c in range(clusters)
        )
        body = (
            "    uint32_t cid = flex_get_cluster_id();\n"
            "    if (flex_get_core_id() == 0) {\n"
            "        for (volatile uint32_t spin = 0; spin < 600 * cid; ++spin) {}\n"
            f"        *(volatile uint32_t*)local(0x{TCDM[0]:x}) = cid + 1;\n"
            "    }\n"
            f"    {row['fn']}();\n"
            f"    if (cid == 0 && flex_is_dm_core()) {{\n{reads}        flex_dma_async_wait_all();\n    }}\n"
            "    flex_intra_cluster_sync();\n"
            f"    if (cid == 0 && flex_get_core_id() == 0) {{\n{dump(TCDM[1], 32, clusters)}    }}\n"
        )
        return frame(row["code"], '#include "flex_dma_pattern.h"\n' + data, body), [1, 2, 3, 4]
    raise KeyError(f"{name}: no driver for kind {kind!r}")


def cluster0(body: str) -> str:
    """``body`` on every core of cluster 0 (it holds role guards and cluster syncs of its own)."""
    indented = "".join(f"    {line}\n" if line else "\n" for line in body.splitlines())
    return f"    if (flex_get_cluster_id() == 0) {{\n{indented}    }}\n"


def frame(code: str, data: str, body: str) -> str:
    """The SDK's program frame (runtime/app_example/main.c) around ``body``, after the row's code."""
    return (
        '#include <stdint.h>\n#include <stddef.h>\n#include "flex_runtime.h"\n#include "flex_printf.h"\n\n'
        f"{code.strip()}\n\n{data}\n"
        "int main() {\n    flex_barrier_xy_init();\n    flex_global_barrier_xy();\n"
        f"{body}"
        "    flex_global_barrier_xy();\n    flex_eoc(0);\n    return 0;\n}\n"
    )


def reference(row: dict) -> list[float]:
    """The float64 results of a vector or matrix row on the inputs :func:`program` draws."""
    kind, op, dtype = row["kind"], row["op"], row["dtype"]
    if kind == "mma":
        m, n, k = MMA
        a, b, c = (draw("mma", "f16", count, seed) for seed, count in enumerate((m * k, k * n, m * n)))
        return [c[i * n + j] + sum(a[i * k + p] * b[p * n + j] for p in range(k)) for i in range(m) for j in range(n)]
    arity = {"binary": 2, "fma": 3, "move": 1, "reduction": 1}[kind]
    xs = [draw(op, dtype, VECTOR_N, seed) for seed in range(arity)]
    if kind == "reduction":
        return [sum(xs[0]) if op == "reduce_add" else max(xs[0])]
    if kind == "move":
        return xs[0]
    if kind == "fma":
        return [a * b + c for a, b, c in zip(*xs, strict=True)]
    combine = {"add": lambda x, y: x + y, "mul": lambda x, y: x * y}[op]
    return [combine(x, y) for x, y in zip(*xs, strict=True)]


def compare(row: dict, words: list[int], exact: list[int]) -> tuple[bool, float | None, str]:
    """Whether the printed ``words`` match: bit-exact for a copy or a sync, within ``tol`` (max error over max
    reference) for arithmetic."""
    if row["kind"] in ("dma_1d", "dma_2d", "sync_cluster", "barrier_global"):
        if len(words) != len(exact):
            return False, None, f"printed {len(words)} words, expected {len(exact)}"
        wrong = [i for i, (w, e) in enumerate(zip(words, exact, strict=True)) if w != e]
        return not wrong, 0.0 if not wrong else 1.0, f"{len(wrong)} words differ, first at {wrong[0]}" if wrong else ""
    dtype = "f16" if row["kind"] == "mma" else row["dtype"]
    want = reference(row)
    if len(words) != len(want):
        return False, None, f"printed {len(words)} words, expected {len(want)}"
    got = [value(w, dtype) for w in words]
    scale = max(abs(x) for x in want) or 1.0
    rel = max(abs(g - w) for g, w in zip(got, want, strict=True)) / scale
    return (
        rel <= row["tol"],
        rel,
        "" if rel <= row["tol"] else f"max error {rel:.3g} over max |reference| > {row['tol']}",
    )


def errors(text: str) -> str:
    """The compiler's error lines of ``text`` (the SDK headers warn a lot), else its tail."""
    found = [line for line in text.splitlines() if "error" in line]
    return "\n".join(found)[:600] if found else text[-600:]


def expand(argv: list[str], **paths: str) -> list[str]:
    return [a.format(**paths) for a in argv]


def run_row(row: dict, spec: dict, root: pathlib.Path) -> dict:
    """Build and run one row in its own folder; its verdict."""
    folder = root / f"{row['name']}-{row['dtype']}"
    folder.mkdir(parents=True)
    paths = {"sdk": os.environ["SOFTHIER_SDK"]}
    verdict = {"name": row["name"], "dtype": row["dtype"], "ok": False, "rel": None, "error": ""}
    (folder / "alloy.c").write_text(row["code"])
    alone = subprocess.run(expand(spec["compile"], **paths), cwd=folder, capture_output=True, text=True, check=False)
    if alone.returncode != 0:  # the answer's build line on the row's code alone
        return verdict | {"error": f"build: {errors(alone.stderr)}"}
    source, exact = program(row)
    (folder / "test.c").write_text(source)
    linked = subprocess.run(
        expand(spec["link"], **paths) + ["test.c"], cwd=folder, capture_output=True, text=True, check=False
    )
    if linked.returncode != 0:
        return verdict | {"error": f"link: {errors(linked.stderr)}"}
    gvsoc = os.path.join(os.environ["SOFTHIER_GVSOC"], "install", "bin", "gvsoc")
    env = os.environ | {"SOFTHIER_ARCH_FILE": str(root / "arch.py")}
    try:
        done = subprocess.run(
            [gvsoc, *expand(spec["run"], **paths), "--work-dir", str(folder)],
            cwd=folder, env=env, capture_output=True, text=True, check=False, timeout=spec.get("timeout", 900),
        )  # fmt: skip
    except subprocess.TimeoutExpired:
        return verdict | {"error": "the simulation timed out"}
    (folder / "gvsoc.log").write_text(done.stdout + done.stderr)
    words = [int(line.split()[1], 16) for line in done.stdout.splitlines() if line.startswith("ALLOY ")]
    if done.returncode != 0:
        return verdict | {"error": f"gvsoc exit {done.returncode}: {(done.stdout + done.stderr)[-600:]}"}
    ok, rel, error = compare(row, words, exact)
    return verdict | {"ok": ok, "rel": rel, "error": error}


def main(path: str) -> int:
    spec = json.loads(pathlib.Path(path).read_text())
    with tempfile.TemporaryDirectory(prefix="alloy_softhier_", dir=spec.get("scratch")) as tmp:
        root = pathlib.Path(tmp)
        (root / "arch.py").write_text(spec["arch"])
        # the SDK headers include flex_cluster_arch.h by quotes, from their own folder: it is replaced there
        sdk = os.environ["SOFTHIER_SDK"]
        include = os.path.join(sdk, "runtime", "runtime", "include")
        subprocess.run([sys.executable, os.path.join(sdk, "utilities", "config.py"), str(root / "arch.py"),
                        "--output-dir", include], check=True, capture_output=True)  # fmt: skip
        with concurrent.futures.ThreadPoolExecutor(max_workers=spec.get("jobs", 4)) as pool:
            futures = [pool.submit(run_row, row, spec, root) for row in spec["rows"]]
            for row, future in zip(spec["rows"], futures, strict=True):
                try:
                    verdict = future.result()
                except Exception as exc:  # one row's harness failure is that row's verdict
                    verdict = {
                        "name": row["name"],
                        "dtype": row["dtype"],
                        "ok": False,
                        "rel": None,
                        "error": f"harness: {exc!r}",
                    }
                print("SOFTHIER-VERDICT " + json.dumps(verdict), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
