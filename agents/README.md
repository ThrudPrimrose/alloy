# agents: the agent studies on targets outside the training data

One runner (`run_agent.py`), one pair of help tools (`tools/`: `ask` is the Alloy ISA lookup, `docs` a vendor
documentation tree), and one folder per study with its SPEC.md, tasks.json, briefs and judge.

| Study | Folder | Judge and timing | Where the episode runs |
|---|---|---|---|
| Tenstorrent Blackhole | `tensix/` (`agents/` and `rows/` as in alloy-tenstorrent) | `tensix/agents/host.py` on the card, median of 5 runs against ttnn's stock ops | ault (files only, no compiler); graded on the card by `tensix/export.sh` into alloy-tenstorrent and a push there (Daisytuner) |
| SoftHier v1 | `softhier/` | `softhier/host.py` on GVSoC: simulated ns of the kernel call against a scalar reference kernel | ault, inside the SoftHier v1 image; the `run` tool is the judge itself |

    python agents/run_agent.py TASK CONFIG OUT --endpoint ENDPOINT.json --study tensix|softhier --tokens 2500000

Configurations: `none`, `docs`, `tool` (and `facts` for the Tenstorrent pilot). The E3 ablation's budget is 2.5M
tokens per run for every configuration (owner, 11-23). `python agents/test_run_agent.py` is the runner's self-check.

`agents/e3.sh softhier|tensix ENDPOINT_RUN_DIR [TASKS...]` runs the whole E3 grid for one study as one ault job
against a vLLM endpoint (`/scratch/ybudanaz/vllm/serve.sbatch`); its header says where the outputs go.

`softhier/baseline_ns.json`: the scalar reference's simulated time per task (ns), every reference passing the judge
on GVSoC (ault jobs 921970, 922070, 922085, 11-23).
