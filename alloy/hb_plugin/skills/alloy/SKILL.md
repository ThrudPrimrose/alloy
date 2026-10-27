---
name: alloy
description: Alloy renders the kernel's loop nests as plain C/C++ variants and builds the best into a library.
when: Before writing C/C++ by hand, and whenever a faster compiler or flag choice per loop nest might pay off.
---

# Alloy

One call (`alloy_profile` or `alloy_speculative`, whichever your setup offers) answers with:

- `library` and `workspace_bytes`: a library in the bench C ABI, ready to `submit` as
  `library=<library>` and `workspace_bytes=<workspace_bytes>`.
- `folder`: `program.c` (the entry, CPF calling one function per scope) and `scopes/<symbol>.c|.cpp`, one
  translation unit per loop nest ("scope"), each the candidate Alloy chose.
- `make`: rebuilds the library from those files. The `Makefile` compiles every scope with its own compiler and
  flags (`scopes` lists them); keep `-ffast-math` on a scope's compile line, never on the link line.
- `report`: the program tree, every scope's candidates (language, compiler, ISA, FP mode, layout knobs) and the
  top ones ranked by measured time (profile) or by prediction (speculative).

How to use it:

1. Call the tool once and `score` the library it built: that is your starting point.
2. Read the report. A scope whose top candidates are close is not worth your time; one where the chosen candidate
   is far behind the roofline, or where the report notes missed vectorization, is.
3. Edit that scope's translation unit (or swap in another candidate's source from the report), change its compile
   line in the `Makefile` if a different compiler or flag set ranked better, run `make`, and `score` again.
4. Submit the best library you measured.
