## Writing for an unfamiliar accelerator
The target may be a processor you saw little of in training, and what you recall may belong to another version of its
SDK. Before you write a kernel, settle each of these and note in your notes how you settled it:

1. The SDK version the task names. Function names, signatures, template arguments and header paths change between
   versions; use the spelling of that version and do not mix spellings of two versions.
2. The entry point of each kernel: the function name and signature, the namespace or macro around it, and what the
   host passes in, as that version expects them.
3. The include line of every call: an undeclared name or a header that does not exist fails the build, and nothing
   here builds the kernel for you.
4. The accuracy of every built-in math function and of the data path (storage format, registers, accumulator)
   against the task's tolerance. A built-in function may be faster than it is accurate; when its accuracy is
   unknown or too low, compute the function another way that meets the tolerance.
5. Every call you write from memory rather than from a source: list it, so a reader can check it.
