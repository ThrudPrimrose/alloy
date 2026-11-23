# Questions for the owner

1. The stock `log_tile` misses the f32 tolerance on tt-metal 0.63 (help tool card probe: abs error 0.012 to 0.0165). I used a custom SFPU log (SFPI rung `alloy_log_f32_sfpi`) instead of `log_tile`. Is a custom SFPU function inside the compute kernel acceptable for this task, or should the kernel use `log_tile` as the spec's op name implies?
2. The rung's card measurement comes from the help tool, not from a run I made. Can you confirm it on the host before scoring?
3. Is `copy_tile_init(cb)` (CB argument) or `copy_tile_init()` (no argument) the right spelling for 0.63?
