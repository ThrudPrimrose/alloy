# Copyright 2026 ETH Zurich and the Alloy authors.
"""What the fork server of every checking child imports once (:func:`alloy.evaluate.verify.child_context`), under
Alloy's OpenMP settings. numpy's OpenBLAS may link the OpenMP runtime (the HB judge image's does), which then reads
its settings here, before any child exists: it binds no thread, so the threads of a child stay on the cores that child
is bound to, and each child sets its own team (:func:`alloy.evaluate.verify.set_team`)."""

import os

os.environ["OMP_PROC_BIND"] = "false"

import dace  # noqa: F401
import numpy  # noqa: F401
