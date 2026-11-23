# Tenstorrent Blackhole kernels: task spec (tt-metal 0.63)

You write the DEVICE kernels of one tt-metal program for a Tenstorrent Blackhole p150 card running tt-metal / ttnn
0.63 (container `daisytuner/x64-tenstorrent:0.63.0-latest`). The host side is fixed and written by us: it creates the
tensors, circular buffers and runtime arguments below, runs your kernels on ONE Tensix core through
`ttnn.generic_op`, and compares the output with a float64 reference. There is no device and no tt-metal here: you
cannot compile or run. Write carefully, and say what you are unsure of.

## Deliverables (in your folder)

- `reader.cpp`: data-movement kernel (RISC-V BRISC) that reads input tiles from DRAM into circular buffers.
- `compute.cpp`: compute kernel (TRISC) that computes the result tiles.
- `writer.cpp`: data-movement kernel (NCRISC) that writes output tiles to DRAM.
- `config.json`: `{"fp32_dest_acc_en": bool, "math_approx_mode": bool, "math_fidelity": "HiFi4|HiFi3|HiFi2|LoFi",
  "unpack_to_dest_fp32": [cb indices], "extra_cbs": [{"index": int, "tiles": int, "format": "float32|bfloat16"}]}`.
- `NOTES.md`: your design in a few lines, and every API spelling you are unsure of.
- `QUESTIONS.md`: anything you would ask the owner instead of guessing (leave empty if none).

Each `.cpp` is a complete kernel source: includes plus `void kernel_main()` (data movement) or the compute kernel entry
point that tt-metal 0.63 expects.

## The fixed host contract

All tensors are interleaved in DRAM, TILE layout (32x32 tiles), one Tensix core.

### Elementwise kernels (fuse_diamond, tsvc_2_s451, transc_log_wide)

- Data: float32, n = 1,048,576 elements = 1024 tiles per array.
- Circular buffers created by the host: CB 0 = input 0, CB 1 = input 1 (only if the kernel has two inputs), CB 16 =
  output; each holds 2 tiles, float32. More CBs only via `extra_cbs` in config.json.
- Reader: runtime args `[num_tiles, in0_addr, in1_addr?]`; compile-time args = `TensorAccessorArgs` of input 0
  followed by those of input 1 (so input 1's accessor args start at the offset equal to input 0's count).
- Writer: runtime args `[num_tiles, out_addr]`; compile-time args = `TensorAccessorArgs` of the output.
- Compute: runtime args `[num_tiles]`.

Kernels:
1. `fuse_diamond`: one input `a`; `t = a*a; u = t + 1; v = t - 1; out = u*v`. Inputs uniform in [-2, 2].
   Tolerance |got - ref| <= 1e-5 + 1e-3 |ref|.
2. `tsvc_2_s451`: inputs `b` (CB 0) and `c` (CB 1); `out = sin(b) + cos(c)`. Inputs uniform in [-pi, pi].
   Tolerance |got - ref| <= 1e-5 + 1e-3 |ref|.
3. `transc_log_wide`: one input `x`; `out = log(x)`, x uniform in log-space over [1e-3, 1e3].
   Tolerance |got - ref| <= 1e-5 + 1e-3 |ref|.

### Tile matmul

- `C = A x B`, A is M x K, B is K x N, M = N = K = 512 (16 x 16 tiles each). A and B are bfloat16, C is float32
  (accumulate in float32).
- CBs: CB 0 = A tiles (bfloat16), CB 1 = B tiles (bfloat16), CB 16 = C tiles (float32); 2 tiles each by default; more
  or larger via `extra_cbs` (to resize CB 0/1/16, list them there with the new tile count).
- Reader: runtime args `[Mt, Kt, Nt, a_addr, b_addr]`; compile-time args = accessor args of A then of B. A and B
  tiles are row-major in tile index (tile (i, j) of A has index i*Kt + j).
- Writer: runtime args `[num_out_tiles, c_addr]` (= Mt*Nt, tile index i*Nt + j); compile-time = accessor args of C.
- Compute: runtime args `[Mt, Kt, Nt]`.
- Tolerance: relative Frobenius error <= 1e-2 against the float64 product of the bfloat16-rounded A and B.

### Eval tasks (agents/tasks.json): the whole device

Each task is one bench kernel as a program over whole arrays (`name = expression` lines; `sum(e)` adds every element
of `e` into one value). Its inputs, in the order the task lists them, are float32 arrays of 1,048,576 elements
(1024 tiles), drawn uniformly from each input's range. Your three kernels run on EVERY Tensix core of the device's
compute grid (`compute_with_storage_grid_size()`); the host splits the 1024 tiles into contiguous ranges, as even as
possible, one per core (every core gets at least one tile). Core index = y * grid_x + x.

- Circular buffers on every core: CB 0, 1, 2 = inputs 0, 1, 2 (as many as the task has), CB 16 = output; each holds
  2 tiles, float32. More CBs only via `extra_cbs` in config.json.
- Reader: runtime args `[num_tiles, start_tile, in0_addr, in1_addr?, in2_addr?]`: this core reads tiles
  `start_tile .. start_tile + num_tiles - 1` of each input; compile-time args = `TensorAccessorArgs` of each input in
  order (input k's start at the sum of the earlier inputs' counts).
- Compute: runtime args `[num_tiles]`.
- A map task writes output tiles at the same indices. Writer: runtime args `[num_tiles, start_tile, out_addr]`;
  compile-time args = `TensorAccessorArgs` of the output.
- A reduce task writes ONE tile per core, float32 partial sums, at output tile index = the core's index; the host
  adds every element of every core's tile in float64, and that sum is the result (any split of the terms is fine).
  Writer: runtime args `[1, core_index, out_addr]`; compile-time args = `TensorAccessorArgs` of the output.
- Tolerance: |got - ref| <= 1e-5 + 1e-3 |ref| for every element, where ref is the float64 program on the float32
  inputs; a reduce task's result may also drift by 2^-23 * sqrt(1,048,576) |ref| (fp32 reassociation, the bench's
  allowance).
- Time: the median of 5 runs of the whole program, compared with the same program in ttnn's stock ops on the same
  device (also the whole grid).

## Scoring

Correct first (within tolerance), then device time per run (median of 5 runs, measured by the host). A kernel that
fails to compile or is wrong scores zero.
