One tool besides `run`: `ask`, the Alloy ISA lookup (checked instruction facts per target, run on GVSoC). Use it as
often as you like; each answer is capped at 400 lines. Start with `ask isas` and `ask --help`.

    ask lookup softhier OP DTYPE   # a SoftHier row: the C to call, the build line, its checked error
    ask ask softhier OP --x ...    # a request with operands (mma, copy, wait, vector ops)
    ask ops                        # the operations
