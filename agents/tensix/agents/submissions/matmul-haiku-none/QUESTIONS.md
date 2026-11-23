1. Which include root and entry point does 0.63 use for compute kernels: `void kernel_main()` or `void MAIN`?
2. Should the matmul use `compute_kernel_hw_startup` instead of `mm_init`?
3. Is HiFi4 acceptable for the score, or may I use HiFi2 or LoFi if device time matters more than margin?
4. May I grow CB 0/1 beyond 8 tiles, or enlarge the output CB, to trade L1 for overlap?
