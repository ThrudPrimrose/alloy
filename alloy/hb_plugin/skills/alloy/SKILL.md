---
name: alloy
description: "How to use Alloy's one tool (alloy_profile or alloy_speculative): it renders every loop nest of the kernel as C/C++ candidates, builds the best per nest into a library you can score, and hands you the sources, a Makefile and a ranked report to improve from. Read it whenever an Alloy tool is in your tool list, before writing any C/C++ by hand."
when: Before writing C/C++ by hand, and whenever a faster compiler or flag choice per loop nest might pay off.
---

# Alloy

One call (`alloy_profile` or `alloy_speculative`, whichever your setup offers) answers with:

- `library` and `workspace_bytes`: a library in the bench C ABI, ready to `submit` as
  `library=<library>` and `workspace_bytes=<workspace_bytes>`.
- `folder`: `program.c` (the entry, CPF calling one function per scope) and `scopes/<symbol>.c|.cpp`, one
  translation unit per loop nest ("scope"), each the candidate Alloy chose.
- `make`: rebuilds the library from those files. The `Makefile` compiles every scope with its own compiler and
  flags (`scopes` lists them). Keep `-ffast-math` on a scope's compile line, never on the link line: linked, it
  switches the whole process to flush-to-zero, which changes every other scope's results and can fail
  verification.
- On a HIP task the answer is the GPU form: `folder` holds `program.hip` (host) and `device.hip` (kernels) with each
  device map at the threadblock its compiler report ranks first, `library` is what the bench builds from them,
  `report` lists every map's ranked shapes, and `make` is the bench's own build command. Edit `device.hip` and
  submit the pair as `source` and `device_source`, or submit the library.
- `advice`: for each scope Alloy left short, why, and the intrinsics its tasklets need on this machine.
- `report`: the program tree, every scope's candidates (language, compiler, ISA, FP mode, layout knobs) and the
  top ones ranked by measured time (profile) or by prediction (speculative).

What a call costs and when it pays off: one call builds and checks every candidate of every scope, which takes
minutes per scope (`alloy_speculative` builds without timing and is faster than `alloy_profile`), and a second call
repeats that work in a new folder. It pays off when the kernel's time sits in loop nests whose best compiler, flags or
FP level you do not know; it does not when you already have a faster version of your own, or when the kernel is one
small loop the compiler vectorizes anyway. Your prompt says whether to call it first; without such a line, the
choice is yours.

When you have called it:

1. `submit` the library it built if nothing you have scores better: that records it (`score` records nothing).
2. Read the report. A scope whose top candidates are close is not worth your time, because Alloy already tried what
   a flag change would; one where the report notes missed vectorization is.
3. Edit that scope's translation unit (other candidates' sources are in `../scopes/<symbol>/variants/` next to
   `folder`), change its compile line in the `Makefile` if a different compiler or flag set ranked better, run
   `make`, and `score` again. A scope in `advice` is the first place to look. `alloy_profile` keeps the default build
   unless a candidate's timing clearly beats it, so rank 1 may not be what it built.
4. Submit the best library you measured.

For a scope you rewrite with intrinsics, the `alloy-isa` skill covers the `alloy_isa` tool.
