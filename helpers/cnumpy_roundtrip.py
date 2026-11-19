# Copyright 2026 ETH Zurich and the Alloy authors.
"""Round trip of the C-to-NumPy lifter over the HPCAgent-Bench corpus: each kernel's NumPy goes to C (the bench's
emitter), the C comes back to NumPy (:mod:`alloy.frontend.cnumpy`), and the lifted kernel runs against the bench's
reference on preset S at the bench's tolerance. ``--reference`` lifts the hand-written ``*_reference.c`` instead.

The bench's numerical oracle supplies inputs, reference outputs and tolerance (``run_kernel``); its native call is
replaced by a call of the lifted kernel, and its compile by a no-op.

    ulimit -s "$(ulimit -H -s)"; export OMP_STACKSIZE=512M OMP_THREAD_LIMIT=$(nproc)  # the oracle's launch env
    python helpers/cnumpy_roundtrip.py llr40 scicomp40 loop_level_reasoning --out roundtrip.json [--reference]
"""

import argparse
import collections
import contextlib
import importlib.util
import inspect
import json
import pathlib
import sys
import time
from collections.abc import Iterator
from typing import Any

import numpy as np
from hpcagent_bench import numerical_oracle, paths, tags
from hpcagent_bench.spec import KERNELS, BenchSpec

from alloy.frontend import cnumpy

#: Statuses of one kernel: the lifted kernel matched, the lifter refused the C, the lifted kernel was wrong (a
#: mismatch or an exception), the bench emits no C for it, or the bench's oracle skips it.
VERDICTS = ("ok", "refused", "wrong", "no-c", "skipped")


def lifted_module(source: str, binding: dict[str, Any], folder: pathlib.Path) -> pathlib.Path:
    module = folder / "lifted_kernel.py"
    module.write_text(cnumpy.translate(source, binding))
    return module


def call_lifted(
    module_path: pathlib.Path,
    binding: dict[str, Any],
    by: dict[str, Any],
    syms: dict[str, Any],
    expected: dict[str, np.ndarray],
    compare: list[str],
    rtol: float,
    atol: float,
) -> str:
    """The lifted kernel on the oracle's inputs, compared as the oracle compares a native backend."""
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        return "wrong:not-importable"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kernel = module.kernel
    wanted = inspect.signature(kernel).parameters
    call = {n: (v.copy() if isinstance(v, np.ndarray) else v) for n, v in by.items()}
    kwargs: dict[str, Any] = {}
    for arg in binding["args"]:
        name, kind = arg["name"], arg["kind"]
        python = cnumpy.python_identifier(name)
        if kind.startswith("ptr_"):
            buffer = np.ascontiguousarray(call[name], dtype=numerical_oracle.np_dtype_for_kind(kind, np.float64))
            call[name] = buffer
            value: Any = buffer.reshape(numerical_oracle.binding_shape(arg, syms))
        else:
            value = call.get(name, syms.get(name))
            if value is None:
                return f"wrong:unresolved:{name}"
        if python in wanted:
            kwargs[python] = value
    try:
        kernel(**kwargs)
    except Exception as exc:
        return f"wrong:raised:{type(exc).__name__}: {str(exc)[:160]}"
    for name in compare:
        got = numerical_oracle.comparison_array(call[name])
        if got.shape != expected[name].shape:
            return f"wrong:shape:{name}"
        if got.size and not numerical_oracle.outputs_match(got, expected[name], rtol, atol):
            return "wrong:" + numerical_oracle.mismatch_detail(name, got, expected[name], rtol, atol)
    return "ok"


@contextlib.contextmanager
def lifted_backend(reference: pathlib.Path | None) -> Iterator[None]:
    """The oracle's C backend replaced by the lifted kernel: of the emitted C, or of ``reference``."""
    invoke, build = numerical_oracle.invoke_isolated, numerical_oracle.native_build_command

    def lifted_invoke(
        backend: str,
        binding: dict[str, Any] | None,
        so: pathlib.Path,
        by: dict[str, Any],
        syms: dict[str, Any],
        expected: dict[str, np.ndarray],
        compare: list[str],
        rtol: float,
        atol: float,
        index_names: frozenset[str],
    ) -> str:
        assert binding is not None
        source = reference if reference is not None else so.parent / binding["sources"]["c"]
        try:
            module = lifted_module(source.read_text(), binding, so.parent)
        except cnumpy.Refused as why:
            return f"refused:{why.reason}: {why}"

        def compute() -> str:
            return call_lifted(module, binding, by, syms, expected, compare, rtol, atol)

        return numerical_oracle.forked_status(compute, numerical_oracle.INVOKE_TIMEOUT_S, expired="wrong:timeout")

    def no_build(backend: str, src: pathlib.Path, so: pathlib.Path, short: str) -> list[str]:
        return ["true"]

    numerical_oracle.invoke_isolated = lifted_invoke
    numerical_oracle.native_build_command = no_build
    try:
        yield
    finally:
        numerical_oracle.invoke_isolated, numerical_oracle.native_build_command = invoke, build


def verdict(status: str) -> str:
    if status == "ok":
        return "ok"
    if status.startswith("refused:"):
        return "refused"
    if status.startswith(("wrong:", "FAIL:crash", "FAIL:timeout")):
        return "wrong"
    if status.startswith("FAIL:emit") or status.startswith("skip:native") or status == "FAIL:no-source":
        return "no-c"
    return "skipped"


def kernels(corpus: str) -> list[str]:
    """The kernel stems of a study tag (``llr40``) or a track (``loop_level_reasoning``)."""
    keys = tags.resolve(corpus) if tags.tag_file(corpus).is_file() else KERNELS.select_keys(corpus)
    return [key.rsplit("/", 1)[-1] for key in keys]


def reference_source(short: str) -> pathlib.Path | None:
    spec = BenchSpec.load(short)
    path = paths.BENCHMARKS / spec.relative_path / f"{spec.module_name}_reference.c"
    return path if path.is_file() else None


def run_one(short: str, reference: bool) -> str:
    source = reference_source(short) if reference else None
    if reference and source is None:
        return "skip:no-reference-c"
    with lifted_backend(source):
        try:
            status = numerical_oracle.run_kernel(short, only_backends={"c"})
        except Exception as exc:
            return f"skip:oracle:{type(exc).__name__}: {str(exc)[:160]}"
    return status.get("c", "skip:no-c-status")


def table(results: dict[str, dict[str, str]]) -> str:
    """Counts per corpus and the refusal reasons with their counts, as Markdown."""
    lines = ["| corpus | kernels | " + " | ".join(VERDICTS) + " |", "|---" * (len(VERDICTS) + 2) + "|"]
    reasons: collections.Counter[str] = collections.Counter()
    for corpus, statuses in results.items():
        counts = collections.Counter(verdict(s) for s in statuses.values())
        lines.append(f"| {corpus} | {len(statuses)} | " + " | ".join(str(counts[v]) for v in VERDICTS) + " |")
        reasons.update(s.split(":", 2)[1] for s in statuses.values() if verdict(s) == "refused")
    lines += ["", "| refusal reason (all corpora, with repeats) | count |", "|---|---|"]
    lines += [f"| {reason} | {count} |" for reason, count in reasons.most_common()]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("corpora", nargs="+", help="study tags (llr40, scicomp40) or tracks (loop_level_reasoning)")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="JSON of every kernel's status")
    parser.add_argument("--reference", action="store_true", help="lift the hand-written *_reference.c")
    parser.add_argument("--only", default="", help="comma-separated kernel stems to restrict to")
    args = parser.parse_args(argv)
    only = {k for k in args.only.split(",") if k}
    results: dict[str, dict[str, str]] = {}
    done: dict[str, str] = {}
    for corpus in args.corpora:
        results[corpus] = {}
        for short in kernels(corpus):
            if only and short not in only:
                continue
            if short not in done:
                start = time.monotonic()
                done[short] = run_one(short, args.reference)
                print(f"{short}: {done[short][:200]} ({time.monotonic() - start:.1f} s)", flush=True)
            results[corpus][short] = done[short]
            args.out.write_text(json.dumps(results, indent=1, sort_keys=True))
    print(table(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
