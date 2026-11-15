# Skill evals of the benchmark packet skills

The packet skills (`alloy/hb_plugin/skills/`) are copied into the agent's sandbox, so their test cases live here
instead, where no agent sees them. `evals/alloy/` holds the cases of the `alloy` skill page, in the layout
`claude plugin eval` reads (one folder per case: `prompt.md`, `case.yaml`, `graders/`). To run them, copy the folder
next to that skill's `SKILL.md` in a scratch copy of the skill. The standalone `skills/alloy-isa-cli/` keeps its
cases in its own `evals/`.
