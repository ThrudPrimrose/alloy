# Copyright 2026 ETH Zurich and the Alloy authors.
from alloy import machine

machine.limit_memory(0.75)  # an oversized test fails with MemoryError instead of exhausting the machine
