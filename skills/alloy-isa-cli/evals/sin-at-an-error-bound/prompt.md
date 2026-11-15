---
tags: [alloy]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

My AVX-512 loop calls sin() on doubles in [-10, 10] and an absolute error of 1e-12 is fine for us. Give me the cheapest vectorized sin I can paste in, and tell me its error.
