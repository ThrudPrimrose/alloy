One tool: `ask`, the Alloy ISA lookup (checked instruction facts per target). Use it as often as you like; each
answer is capped at 400 lines. Start with `ask isas` and `ask --help`.

    ask lookup tensix OP DTYPE   # a Tensix row: init and call per tt-metal version, includes, checked error
    ask ask tensix OP --x ...    # a request with operands
    ask ops                      # the operations
