# Copyright 2026 ETH Zurich and the Alloy authors.
from alloy import machine

# an oversized test fails with MemoryError instead of exhausting the machine
machine.limit_memory(0.75, len(machine.physical_cores()))
