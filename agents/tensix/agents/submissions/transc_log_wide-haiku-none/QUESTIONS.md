# Questions for the owner

1. Include paths and entry point: do you want me to use the `api/...` include style and `void kernel_main()` for the
   compute kernel, or the older `compute_kernel_api/...` and `void MAIN` style? I wrote the newer form from memory.
2. Accuracy near x = 1: the tolerance has an absolute term of 1e-5, and log(x) is near 0 there. I use the exact SFPU
   log (`math_approx_mode=false`). If you have a measured error for the exact log on this card, please share it.
3. Throughput: CB 0 and CB 16 are fixed at 2 tiles by the host, and I did not resize them. Is it allowed to request
   deeper CBs through `extra_cbs` for elementwise kernels, or does the contract forbid that?
