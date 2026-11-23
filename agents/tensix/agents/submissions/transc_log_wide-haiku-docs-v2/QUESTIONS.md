# QUESTIONS for the owner

1. Accuracy of the built-in SFPU log. The Blackhole `log_tile` polynomial (3rd order on the mantissa) may not meet
   the absolute part of the tolerance (1e-5) near x = 1, where ref is about 0. Should I (a) keep `log_tile<false>`
   as written, (b) add a refinement step, for example `y = y0 + x * exp(-y0) - 1` using `exp_tile`, which I could not
   check for accuracy either, or (c) accept a documented miss on the x near 1 band? I chose (a) and did not verify it.

2. `unpack_to_dest_fp32: [0]`. I assume the host maps this list to the fp32 unpack-to-DST mode for CB 0. Please
   confirm that this is the format the host expects (a list of CB indices, not a list of bools per CB).
