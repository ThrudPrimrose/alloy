# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tensix tile programs from Alloy's checked rows: DaCe's tile nodes as row calls (:mod:`alloy.tensixgen.backend`), a
vectorized map or reduce split into reader, compute and writer kernels under the eval contract v2
(:mod:`alloy.tensixgen.split`), the eval tasks' programs (:mod:`alloy.tensixgen.tasks`), checked on ttsim by
:mod:`alloy.tensixgen.ttsim`."""
