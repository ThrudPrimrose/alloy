# Copyright 2026 ETH Zurich and the Alloy authors.
import os
import resource

from alloy import machine

# An oversized test fails with MemoryError instead of exhausting the machine. The cap is a share of the machine's
# total memory, not of what is free when a worker starts: parallel workers would make it depend on the load. The
# stacks of every CPU OpenMP may start a thread on are reserved, as a judge-run reference starts one per CPU.
TOTAL = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
LIMIT = int(0.75 * TOTAL) + len(os.sched_getaffinity(0)) * machine.openmp_stack_bytes()
_, HARD = resource.getrlimit(resource.RLIMIT_DATA)
CAP = LIMIT if HARD == resource.RLIM_INFINITY else min(LIMIT, HARD)
resource.setrlimit(resource.RLIMIT_DATA, (CAP, CAP))
