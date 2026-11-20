# Copyright 2026 ETH Zurich and the Alloy authors.
"""Tensix tile programs of the eval tasks (``eval_set.admitted()``, which equals alloy-tenstorrent's
``agents/tasks.json``), from DaCe's tile nodes.

    python -m alloy.tensixgen generate OUT [TASK ...] [--version v06|v08] [--dst-block N] [--cores K]
                                       [--placement interleaved|sharded]
    python -m alloy.tensixgen ttsim [TASK ...] [--dst-block N] [--cores K] [--placement ...]   # a container per task
"""

import argparse
import dataclasses
import pathlib
import sys

from alloy.tensixgen import ttsim
from alloy.tensixgen.split import INTERLEAVED, SHARDED, Options
from alloy.tensixgen.tasks import programs


def main(argv: list[str] | None = None) -> int:
    from alloy.hb_plugin import eval_set

    parser = argparse.ArgumentParser(prog="python -m alloy.tensixgen", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    parser.add_argument("command", choices=("generate", "ttsim"))
    parser.add_argument("names", nargs="*", metavar="OUT/TASK", help="generate: the output folder first")
    parser.add_argument("--version", choices=("v06", "v08"), default="v06", help="tt-metal spelling (generate)")
    parser.add_argument("--dst-block", type=int, default=0, help="tiles per DST acquire (0: the most that fit)")
    parser.add_argument("--cores", type=int, default=0, help="cores (0: the whole grid, as contract v2)")
    parser.add_argument("--placement", choices=(INTERLEAVED, SHARDED), default=INTERLEAVED,
                        help="the arrays' placement: interleaved DRAM, or L1 sharded over --cores")  # fmt: skip
    parser.add_argument("--cache", type=pathlib.Path, default=ttsim.default_cache())
    args = parser.parse_args(argv)
    names = list(args.names)
    out = pathlib.Path(names.pop(0)) if args.command == "generate" and names else None
    if args.command == "generate" and out is None:
        parser.error("generate needs the output folder")
    tasks = [dataclasses.asdict(t) for t in eval_set.admitted()[0]]
    unknown = set(names) - {t["name"] for t in tasks}
    if unknown:
        parser.error(f"no task {', '.join(sorted(unknown))}")
    tasks = [t for t in tasks if not names or t["name"] in names]
    options = Options(args.dst_block, args.cores, args.placement)
    if out is not None:
        for p in programs(tasks, options, args.version):
            print(p.write(out / p.name))
        return 0
    failed = 0
    for task in tasks:  # one task per container: a hang or crash stops only its own
        (v,) = ttsim.run_tasks([task], args.cache, options)
        failed += not v.ok
        shown = f"rel {v.err:.3g} abs {v.abs:.3g}" if v.err is not None and v.abs is not None else v.error[:300]
        print(f"{v.name:24} {'ok' if v.ok else 'FAIL'}  {shown}  cores {v.cores}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
