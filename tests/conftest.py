# Copyright 2026 ETH Zurich and the Alloy authors.
import os

from alloy import machine

# an oversized test fails with MemoryError instead of exhausting the machine; the stacks of every CPU OpenMP may
# start a thread on are reserved, as a judge-run reference starts one per CPU, not per physical core
machine.limit_memory(0.75, len(os.sched_getaffinity(0)))
