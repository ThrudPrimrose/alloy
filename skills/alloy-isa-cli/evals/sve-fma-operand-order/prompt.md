---
tags: [alloy]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

I'm hand-writing an SVE loop for y[i] = a*x[i] + y[i] in double precision (a is a scalar). Which ACLE intrinsic call do I write for the multiply-add, with its operands in the right order? Our box is x86, the code runs on a Graviton later.
