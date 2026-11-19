# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tensix tile programs from Alloy's checked rows: a map or reduce scope becomes reader, compute and writer kernels
under the eval contract v2 (:mod:`alloy.tensixgen.generate`), found in an SDFG by :mod:`alloy.tensixgen.dace_pass`
and checked on ttsim by :mod:`alloy.tensixgen.ttsim`."""
