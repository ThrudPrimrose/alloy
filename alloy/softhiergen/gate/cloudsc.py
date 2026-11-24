# Copyright 2026 ETH Zurich and the Alloy authors.
"""CloudSC nests of HPCAgent-Bench as gate cases (:mod:`alloy.gate`) for both tile backends. Each nest is a float32
DaCe transcription of the bench's NumPy reference, its sizes specialized small; the inputs are the bench
initializer's draws (the atmospheric state) and the reference is the bench's NumPy program at float64.

The bench's own DaCe port is not taken: it computes in float64 where NumPy promotes (``numpy.full(shape, 1.0)``, the
Python constants), and neither tile backend computes float64."""

import importlib.util
import pathlib
from collections.abc import Callable
from types import ModuleType

import dace
import numpy
import yaml
from dace.frontend.python.parser import DaceProgram

from alloy.gate import Case

KLEV = dace.symbol("KLEV")
KLON = dace.symbol("KLON")

#: YOMCST / YOETHF constants of dwarf-p-cloudsc, as the bench's reference spells them
RTT = 273.16
RD = 287.0597
RV = 461.5250
RETV = RV / RD - 1.0
R2ES = 611.21 * RD / RV
R3LES, R3IES, R4LES = 17.502, 22.587, 32.19
RTICE = RTT - 23.0
RTWAT_RTICE_R = 1.0 / 23.0


@dace.program
def saturation(
    ztp1: dace.float32[KLEV, KLON],
    pap: dace.float32[KLEV, KLON],
    zfoealfa: dace.float32[KLEV, KLON],
    zfoeewmt: dace.float32[KLEV, KLON],
    zqsmix: dace.float32[KLEV, KLON],
    zfoeew: dace.float32[KLEV, KLON],
    zqsice: dace.float32[KLEV, KLON],
    zfoeeliqt: dace.float32[KLEV, KLON],
    zqsliq: dace.float32[KLEV, KLON],
) -> None:
    """cloudsc_saturation: the saturation humidities over water, ice and the mixed phase (R4IES = -0.7)."""
    clamped = numpy.maximum(RTICE, numpy.minimum(RTT, ztp1)) - RTICE
    zfoealfa[:] = numpy.minimum(1.0, clamped * RTWAT_RTICE_R * (clamped * RTWAT_RTICE_R))
    eliq = numpy.exp(R3LES * (ztp1 - RTT) / (ztp1 - R4LES))
    eice = numpy.exp(R3IES * (ztp1 - RTT) / (ztp1 + 0.7))
    zfoeewm = R2ES * (zfoealfa * eliq + (1.0 - zfoealfa) * eice)
    zfoeewmt[:] = numpy.minimum(zfoeewm / pap, 0.5)
    zqsmix[:] = zfoeewmt / (1.0 - RETV * zfoeewmt)
    zfoeew[:] = numpy.minimum(0.5, numpy.where(ztp1 >= RTT, R2ES * eliq, R2ES * eice) / pap)
    zqsice[:] = zfoeew / (1.0 - RETV * zfoeew)
    zfoeeliqt[:] = numpy.minimum(R2ES * eliq / pap, 0.5)
    zqsliq[:] = zfoeeliqt / (1.0 - RETV * zfoeeliqt)


NCLV = dace.symbol("NCLV")
RLMIN = 1.0e-8
PTSPHY = 50.0


@dace.program
def liq_ice_frac(
    zqx_l: dace.float32[KLEV, KLON],
    zqx_i: dace.float32[KLEV, KLON],
    za: dace.float32[KLEV, KLON],
    zli: dace.float32[KLEV, KLON],
    zliqfrac: dace.float32[KLEV, KLON],
    zicefrac: dace.float32[KLEV, KLON],
) -> None:
    """cloudsc_liq_ice_frac: the clamped cover, the condensate, and its liquid and ice fractions where it is cloudy."""
    za[:] = numpy.maximum(0.0, numpy.minimum(1.0, za))
    zli[:] = zqx_l + zqx_i
    denom = numpy.where(zli > RLMIN, zli, 1.0)
    zliqfrac[:] = numpy.where(zli > RLMIN, zqx_l / denom, 0.0)
    zicefrac[:] = numpy.where(zli > RLMIN, 1.0 - zliqfrac, 0.0)


@dace.program
def init(
    pt: dace.float32[KLEV, KLON],
    pa: dace.float32[KLEV, KLON],
    pq: dace.float32[KLEV, KLON],
    pclv: dace.float32[NCLV, KLEV, KLON],
    ptend_t: dace.float32[KLEV, KLON],
    ptend_a: dace.float32[KLEV, KLON],
    ptend_q: dace.float32[KLEV, KLON],
    ptend_cld: dace.float32[NCLV, KLEV, KLON],
    ztp1: dace.float32[KLEV, KLON],
    za: dace.float32[KLEV, KLON],
    zqx: dace.float32[NCLV, KLEV, KLON],
) -> None:
    """cloudsc_init: the state after one time step of the tendencies; vapour (species NCLV - 1) comes from pq."""
    ztp1[:] = pt + PTSPHY * ptend_t
    za[:] = pa + PTSPHY * ptend_a
    zqx[NCLV - 1, :, :] = pq + PTSPHY * ptend_q
    zqx[: NCLV - 1, :, :] = pclv[: NCLV - 1, :, :] + PTSPHY * ptend_cld[: NCLV - 1, :, :]


#: Each nest: its float32 transcription and the sizes the simulators run in seconds (KLON innermost).
NESTS: dict[str, tuple[DaceProgram, dict[str, int]]] = {
    "cloudsc_saturation": (saturation, {"KLEV": 4, "KLON": 256}),
    "cloudsc_liq_ice_frac": (liq_ice_frac, {"KLEV": 4, "KLON": 256}),
    "cloudsc_init": (init, {"NCLV": 5, "KLEV": 4, "KLON": 256}),
}
#: float32 against a float64 reference through the Magnus exponentials
TOLERANCE = 1e-5


def module(path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, path
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def specialized(program: DaceProgram, sizes: dict[str, int]) -> Callable[[], dace.SDFG]:
    def build() -> dace.SDFG:
        sdfg = program.to_sdfg(simplify=True)
        sdfg.specialize(sizes)
        return sdfg

    return build


def nest_case(name: str, program: DaceProgram, sizes: dict[str, int]) -> Case:
    """``name`` on its bench initializer's draws at ``sizes``; the reference is its bench NumPy program at float64."""
    from hpcagent_bench.spec import KERNELS, BenchSpec

    spec = BenchSpec.load(next(kernel for kernel in KERNELS if kernel.rsplit("/", 1)[-1] == name))
    manifest = yaml.safe_load(spec.sibling(".yaml").read_text())
    names = [k for k, v in manifest["args"].items() if isinstance(v, str) or "shape" in v]  # not decomposition
    drawn = module(spec.sibling(".py")).initialize(**sizes, datatype=numpy.float64)
    arrays = dict(zip(names, (numpy.array(a) for a in drawn), strict=True))
    reference = {k: v.copy() for k, v in arrays.items()}
    vars(module(spec.sibling("_numpy.py")))[name](**reference, **sizes)
    outputs = [k for k in names if isinstance(manifest["args"][k], dict) and manifest["args"][k].get("out")]
    return Case(
        f"CloudSC {name.removeprefix('cloudsc_')} ({' x '.join(f'{k} {v}' for k, v in sizes.items())})",
        specialized(program, sizes),
        {k: v.astype(numpy.float32) for k, v in arrays.items()},
        {k: reference[k] for k in outputs},
        TOLERANCE,
    )


def cloudsc_cases() -> list[Case]:
    return [nest_case(name, program, sizes) for name, (program, sizes) in NESTS.items()]
