---
tags: [alloy]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

In the objdump of my hot loop I see 'vfmadd231pd %zmm2,%zmm1,%zmm0' followed by 'call _ZGVeN8v_exp'. What does each line compute, and in what precision and width?
