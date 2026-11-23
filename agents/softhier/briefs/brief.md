# Brief (identical for every configuration; only the "Help" section differs)

You write one SoftHier v1 kernel for the task in SPEC.md, section "{KERNEL}". Read SPEC.md first: it fixes the
deliverables, the host contract, the inputs and the tolerance. Write the files into this folder.

The `run` tool builds your folder's kernel.c with the judge's own host and inputs and runs it on GVSoC: it answers
whether the result is correct, its error, and the simulated time of your kernel (or the compiler's errors). Use it as
often as you like; the last kernel.c in your folder when you finish is the submission. Make it correct first, then
fast: the score is the time against our scalar reference.

Limits: {LIMITS} (the same for every configuration and model; a run that reaches a limit ends there).

## Help

{HELP}
