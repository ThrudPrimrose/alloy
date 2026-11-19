# Copyright 2026 ETH Zurich and the Alloy authors.
"""GPU candidates (A10): a GPU program's host and device units built into one library along the device axes of
``gpu_matrix.toml``, the compiler and the floating-point level, with the judge's own build recipe
(``hpcagent_bench.languages.build_shared_lib_commands``) where the bench has one, so the default candidate is the
build the judge makes of the same source. A candidate whose compiler or flags this machine does not take fails its
build and drops out (discovery by building), and one whose device object equals an earlier one is a duplicate."""

import hashlib
import pathlib
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, field

from dace.codegen import cpf
from hpcagent_bench import languages
from hpcagent_bench.categories import Language
from hpcagent_bench.flags import Mode

from alloy import gpu

__all__ = [
    "GPU_MATRIX",
    "GpuBuild",
    "GpuCandidate",
    "GpuCompiler",
    "build",
    "candidates",
    "cuda_root",
    "load",
    "resource_key",
    "usage",
]

GPU_MATRIX = pathlib.Path(__file__).with_name("gpu_matrix.toml")
#: The device language of a dialect, and the judge's evaluation mode for it.
LANGUAGE = {"cuda": Language.CUDA, "hip": Language.HIP}
MODE = {"cuda": Mode.GPU_CUDA, "hip": Mode.GPU_HIP}
#: The emission axis on a device unit: where DaCe declares a kernel's scope scalars besides ``eager`` (the default),
#: the choice AMD's compiler answers to. DaCe's other emission knobs do not reach device code: a kernel's pointers are
#: always ``__restrict__`` and its scalars always passed by value.
SCALAR_DECL = ("late", "late_fused")


@dataclass(frozen=True, slots=True)
class GpuCompiler:
    """A device compiler: its dialect; ``bench``, the compilers.yaml block whose recipe builds it ("" for its own
    ``compile`` and ``link`` flags); ``driver`` in place of the block's (""); the flags of each floating-point level
    and of ``atomics``; and link flags its driver needs beyond the recipe's."""

    name: str
    dialect: str
    bench: str
    driver: str
    compile: tuple[str, ...]
    link: tuple[str, ...]
    fp: dict[str, tuple[str, ...]]
    atomics: tuple[str, ...]
    report: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GpuCandidate:
    """One build of a GPU program: a compiler, a floating-point level ("" the compiler's default), whether
    floating-point atomics may take the unsafe hardware path (AMD, a scope with an accumulation), and where the device
    code declares its scalars (DaCe's ``scalar_decl``; "" the default, ``eager``); ``intrinsic``: the device maps
    are rendered with tasklets of the checked SIMT rows (:func:`alloy.backend.intrinsics.device_rendered`)."""

    compiler: str
    fp: str = ""
    unsafe_atomics: bool = False
    scalar_decl: str = ""
    intrinsic: bool = False

    @property
    def name(self) -> str:
        atomics = "unsafe-atomics" if self.unsafe_atomics else ""
        decl, intrinsic = self.scalar_decl and f"decl-{self.scalar_decl}", "intrinsic" if self.intrinsic else ""
        return "_".join(filter(None, (self.compiler, self.fp, atomics, decl, intrinsic)))


def usage(built: "GpuBuild", dialect: str) -> dict[str, gpu.Usage]:
    """Every kernel's registers and spills, from the report the build printed (``report`` flags)."""
    return (gpu.nvcc_usage if dialect == "cuda" else gpu.hip_usage)(built.log)


def resource_key(usages: dict[str, gpu.Usage]) -> tuple[bool, int, int]:
    """How speculative mode ranks a build: no spill first, then fewer spilled bytes, then fewer registers."""
    spills = sum(u.spill_bytes for u in usages.values())
    return spills > 0, spills, sum(u.registers for u in usages.values())


@dataclass(frozen=True, slots=True)
class GpuBuild:
    """A candidate's library, the hash of its device object (equal hashes: one code), and the build log or error."""

    candidate: GpuCandidate
    library: pathlib.Path | None
    device_hash: str
    log: str
    error: str = ""
    duplicate_of: str = field(default="")


def load(path: pathlib.Path = GPU_MATRIX) -> dict[str, GpuCompiler]:
    """Every device compiler of ``path``, by name, in file order."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)["compilers"]
    return {
        name: GpuCompiler(
            name,
            entry["dialect"],
            entry.get("bench", ""),
            entry.get("driver", ""),
            tuple(entry.get("compile", ())),
            tuple(entry.get("link", ())),
            {level: tuple(flags) for level, flags in entry.get("fp", {}).items()},
            tuple(entry.get("atomics", ())),
            tuple(entry.get("report", ())),
        )
        for name, entry in raw.items()
    }


def candidates(compilers: dict[str, GpuCompiler], dialect: str, accumulates: bool) -> list[GpuCandidate]:
    """The default (the dialect's first compiler with no flag) and every single-factor change of it: each other
    compiler, each floating-point level, the unsafe atomics where the program accumulates and the compiler has them,
    each other place for the device code's scalar declarations (:data:`SCALAR_DECL`), and the intrinsic tasklets."""
    own = [c for c in compilers.values() if c.dialect == dialect]
    if not own:
        return []
    first = own[0]
    out = [GpuCandidate(first.name)]
    out += [GpuCandidate(c.name) for c in own[1:]]
    out += [GpuCandidate(first.name, level) for level in first.fp]
    if accumulates and first.atomics:
        out.append(GpuCandidate(first.name, unsafe_atomics=True))
    out += [GpuCandidate(first.name, scalar_decl=place) for place in SCALAR_DECL]
    out.append(GpuCandidate(first.name, intrinsic=True))
    return out


def commands(
    compiler: GpuCompiler, candidate: GpuCandidate, device: pathlib.Path, host: pathlib.Path, library: pathlib.Path,
    arch: str, libraries: tuple[str, ...] = (),
) -> list[list[str]]:  # fmt: skip
    """The compile and link argvs of ``candidate``: the judge's recipe for a bench compiler, else the compiler's
    own flags with ``{arch}`` (``sm_89`` or a ``gfx`` target) and ``{cuda}`` (:func:`cuda_root`) filled in."""
    flags = [
        *compiler.fp.get(candidate.fp, ()),
        *(compiler.atomics if candidate.unsafe_atomics else ()),
        *compiler.report,
    ]
    # what the bench builds a CPF GPU form with (frameworks.dace_emit.device_units): the form's libraries, and for
    # nvcc DaCe's own device flags
    library_compile, library_link = languages.library_build_flags(LANGUAGE[compiler.dialect], libraries)
    if compiler.bench:
        own = [f for f in cpf.CUDA_BUILD_FLAGS if not f.startswith("-std=")] if compiler.bench == "nvcc" else []
        return languages.build_shared_lib_commands(
            LANGUAGE[compiler.dialect], device, library, mode=MODE[compiler.dialect], compiler=compiler.bench,
            cc_override=compiler.driver or None, extra_compile=[*library_compile, *own, *flags],
            extra_link=[*library_link, *compiler.link], extra_sources=[host],
        )  # fmt: skip
    driver = shutil.which(compiler.driver) or compiler.driver
    fill = {"arch": arch, "cuda": cuda_root()}
    compile_flags = [flag.format(**fill) for flag in compiler.compile]
    objects = [unit.with_name(unit.name + ".o") for unit in (device, host)]
    compiles = [
        [driver, *compile_flags, *library_compile, *flags, "-c", str(u), "-o", str(o)]
        for u, o in zip((device, host), objects, strict=True)
    ]
    link = [*(flag.format(**fill) for flag in compiler.link), *library_link]
    return [*compiles, [driver, *[str(o) for o in objects], *link, "-o", str(library)]]


def cuda_root() -> str:
    """The CUDA installation nvcc runs from ("" without nvcc): clang's ``--cuda-path`` and the runtime's folder."""
    nvcc = shutil.which("nvcc")
    return str(pathlib.Path(nvcc).resolve().parent.parent) if nvcc else ""


def device_hash(folder: pathlib.Path, device: pathlib.Path) -> str:
    """The hash of the device unit's object without its symbol table and comments (the same code, the same hash)."""
    obj = device.with_name(device.name + ".o")
    if not obj.is_file():
        return ""
    stripped = folder / "device.stripped.o"
    done = subprocess.run(["strip", "-R", ".comment", "-o", str(stripped), str(obj)], capture_output=True, check=False)
    data = stripped.read_bytes() if done.returncode == 0 else obj.read_bytes()
    return hashlib.sha256(data).hexdigest()[:16]


def build(
    compilers: dict[str, GpuCompiler], candidate: GpuCandidate, host_code: str, device_code: str, folder: pathlib.Path,
    arch: str, libraries: tuple[str, ...] = (),
) -> GpuBuild:  # fmt: skip
    """``candidate``'s library in ``folder/<name>/``, from the CPF GPU form's host and device units and the
    libraries the form calls."""
    compiler = compilers[candidate.compiler]
    where = (folder / candidate.name).resolve()
    where.mkdir(parents=True, exist_ok=True)
    suffix = "cu" if compiler.dialect == "cuda" else "hip"
    # A HIP host unit is named .hip: amdclang++ (clang called directly) compiles a .cpp as plain C++, where
    # hip_runtime.h fails, and a -x hip from the bench's recipe lands after the input, too late; hipcc takes either.
    device, host = where / f"kernel.{suffix}", where / ("kernel_host.hip" if suffix == "hip" else "kernel_host.cpp")
    device.write_text(device_code)
    host.write_text(host_code)
    library = where / f"lib{candidate.name}.so"
    log: list[str] = []
    try:
        argvs = commands(compiler, candidate, device, host, library, arch, libraries)
    except (KeyError, FileNotFoundError) as exc:
        return GpuBuild(candidate, None, "", "", error=f"no recipe: {exc}")
    for argv in argvs:
        try:
            done = subprocess.run(argv, capture_output=True, text=True, check=False, cwd=where)
        except FileNotFoundError as exc:
            return GpuBuild(candidate, None, "", "\n".join(log), error=f"{argv[0]} is not installed: {exc}")
        log.append(" ".join(argv) + "\n" + done.stdout + done.stderr)
        if done.returncode != 0:
            return GpuBuild(candidate, None, "", "\n".join(log), error=(done.stderr.strip() or "failed")[-2000:])
    return GpuBuild(candidate, library, device_hash(where, device), "\n".join(log))
