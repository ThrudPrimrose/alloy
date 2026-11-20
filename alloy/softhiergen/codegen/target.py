# Copyright 2026 ETH Zurich and the Alloy authors.
"""``SoftHierCodeGen``: emits each ``SoftHier_Device`` map as a kernel function of one C++ unit.

Every core of every cluster runs the unit's ``__dsh_program``, which calls the kernels in program order with a
global barrier between them. Cluster c runs iterations c, c + P, ... of the kernel map, flattened. The body is dispatched to DaCe's CPU generator: control flow and scalar tasklets run on every core
(replicated); the expansions of the library nodes guard their effects by core role.

Arrays: a ``SoftHier_TCDM`` array is a static in ``.l1`` (TCDM), at one address on every cluster; a
``SoftHier_HBM`` array is a static in ``.hbm`` (an argument is defined in the data unit). The linker assigns both.
"""

import math

import numpy
from dace import data, dtypes, registry, symbolic
from dace.codegen.codeobject import CodeObject
from dace.codegen.dispatcher import DefinedType
from dace.codegen.prettycode import CodeIOStream
from dace.codegen.target import TargetCodeGenerator
from dace.codegen.targets.cpp import sym2cpp
from dace.codegen.targets.framecode import DaCeCodeGenerator
from dace.memlet import Memlet
from dace.sdfg import SDFG, nodes
from dace.sdfg.graph import MultiConnectorEdge
from dace.sdfg.state import ControlFlowRegion, StateSubgraphView

from alloy.softhiergen.arch import V1, Arch
from alloy.softhiergen.library.common import LoweringError
from alloy.softhiergen.storage import DEVICE, HBM, TCDM

#: The entry function of the unit; the data unit's ``main`` calls it on every core.
ENTRY = "__dsh_program"

SOFTHIER_STORAGES = (TCDM, HBM)


def tcdm_symbol(sdfg: SDFG, name: str) -> str:
    """The static that holds a TCDM array."""
    return f"__dsh_l1_{sdfg.cfg_id}_{name}"


def static_size(desc: data.Data, what: str) -> int:
    size = symbolic.evaluate(desc.total_size, {}) if symbolic.issymbolic(desc.total_size) else desc.total_size
    try:
        return int(size)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
    except TypeError as error:
        raise ValueError(f"{what}: SoftHier arrays need a size known at compile time, got {desc.total_size}") from error


@registry.autoregister_params(name="softhier")
class SoftHierCodeGen(TargetCodeGenerator):
    """The constructor only registers dispatchers: DaCe builds every target on every compile."""

    target_name = "softhier"
    title = "SoftHier"
    language = "cpp"

    def __init__(self, frame_codegen: DaCeCodeGenerator, sdfg: SDFG) -> None:
        self.frame = frame_codegen
        self.dispatcher = frame_codegen.dispatcher
        self.cpu = self.dispatcher.get_generic_node_dispatcher()
        self.sdfg = sdfg
        self.arch: Arch = V1
        self.globals = CodeIOStream()
        self.functions = CodeIOStream()
        self.kernel_code = CodeIOStream()
        self.kernels: list[str] = []
        self.statics: set[str] = set()

        self.dispatcher.register_map_dispatcher(DEVICE, self)
        self.dispatcher.register_array_dispatcher(list(SOFTHIER_STORAGES), self)
        others = (dtypes.StorageType.Register, dtypes.StorageType.Default, dtypes.StorageType.CPU_Heap)
        for softhier in SOFTHIER_STORAGES:
            for other in (*SOFTHIER_STORAGES, *others):
                self.dispatcher.register_copy_dispatcher(softhier, other, None, self)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
                self.dispatcher.register_copy_dispatcher(other, softhier, None, self)  # pyright: ignore[reportArgumentType] -- DaCe's annotation

    # Code objects

    def get_generated_codeobjects(self) -> list[CodeObject]:
        if not self.kernels:
            return []
        code = CodeIOStream()
        code.write('#include "softhiergen/dsh.h"\n')
        for name, (ctype, value) in self.constants().items():
            code.write(f"constexpr {ctype} {name} = {value};")
        for name, desc in self.sdfg.arrays.items():
            if desc.transient:
                continue
            if isinstance(desc, data.Scalar):
                code.write(f'extern "C" const {desc.dtype.ctype} {name};')
            elif desc.storage == HBM:
                code.write(f'extern "C" {desc.dtype.ctype} {name}[];')
        code.write(self.globals.getvalue())
        code.write(self.functions.getvalue())
        code.write(self.kernel_code.getvalue())
        calls = "\n    dsh_global_barrier();\n    ".join(f"{kernel}();" for kernel in self.kernels)
        code.write(f'extern "C" void {ENTRY}(void) {{\n    {calls}\n}}')
        return [
            CodeObject(
                f"{self.sdfg.name}_softhier",
                code.getvalue(),
                "cpp",
                SoftHierCodeGen,
                "SoftHier",
                target_type="softhier",
                linkable=False,
                sdfg=self.sdfg,
            )
        ]

    def constants(self) -> dict[str, tuple[str, str]]:
        found = {}
        for name, value in self.sdfg.constants.items():
            if isinstance(value, numpy.ndarray):
                raise TypeError(f"{name}: SoftHier takes scalar constants only")
            found[name] = (dtypes.dtype_to_typeclass(type(value)).ctype, sym2cpp(value))  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation
        return found

    # Scopes

    def generate_scope(
        self,
        sdfg: SDFG,
        cfg: ControlFlowRegion,
        dfg_scope: StateSubgraphView,
        state_id: int,
        function_stream: CodeIOStream,
        callsite_stream: CodeIOStream,
    ) -> None:
        entry: nodes.MapEntry = dfg_scope.source_nodes()[0]  # pyright: ignore[reportAssignmentType] -- DaCe's annotation
        name = f"__dsh_kernel_{len(self.kernels)}_{entry.map.label}"
        self.kernels.append(name)
        kernel = self.kernel_code
        kernel.write(f"static void {name}(void) {{", cfg, state_id, entry)
        kernel.write("const uint32_t __cid = dsh_cluster_id();")
        self.open_iterations(entry, kernel)
        self.dispatcher.defined_vars.enter_scope(entry)
        for param in entry.map.params:
            self.dispatcher.defined_vars.add(param, DefinedType.Scalar, "int")
        self.frame.allocate_arrays_in_scope(sdfg, cfg, entry, self.functions, kernel)
        self.dispatcher.dispatch_subgraph(
            sdfg, cfg, dfg_scope, state_id, self.functions, kernel, skip_entry_node=True, skip_exit_node=True
        )
        self.frame.deallocate_arrays_in_scope(sdfg, cfg, entry, self.functions, kernel)
        self.dispatcher.defined_vars.exit_scope(entry)
        kernel.write("}\n}\n")
        callsite_stream.write(f"// SoftHier kernel {name}", cfg, state_id, entry)

    def open_iterations(self, entry: nodes.MapEntry, kernel: CodeIOStream) -> None:
        """Opens the loop over the map iterations this cluster runs: cluster c runs iterations c, c + P, ... of the
        map flattened row-major; each parameter is recovered from the flat index with / and %."""
        sizes = entry.map.range.size_exact()
        total = sym2cpp(math.prod(sizes))
        kernel.write(f"for (int __it = __cid; __it < {total}; __it += {self.arch.num_clusters}) {{")
        inner = 1
        for dim in reversed(range(len(sizes))):
            begin, _, step = entry.map.range[dim]
            index = "__it" if inner == 1 else f"__it / {sym2cpp(inner)}"
            if dim > 0:
                index = f"({index}) % {sym2cpp(sizes[dim])}"
            kernel.write(f"const int {entry.map.params[dim]} = {sym2cpp(begin)} + ({index}) * {sym2cpp(step)};")
            inner *= sizes[dim]

    # Arrays

    def declare_array(  # pyright: ignore[reportIncompatibleMethodOverride] -- DaCe's annotation
        self,
        sdfg: SDFG,
        cfg: ControlFlowRegion,
        dfg: StateSubgraphView,
        state_id: int,
        node: nodes.AccessNode,
        nodedesc: data.Data,
        global_stream: CodeIOStream,
        declaration_stream: CodeIOStream,
    ) -> None:
        self.allocate_array(sdfg, cfg, dfg, state_id, node, nodedesc, global_stream, declaration_stream, CodeIOStream())

    def allocate_array(  # pyright: ignore[reportIncompatibleMethodOverride] -- DaCe's annotation
        self,
        sdfg: SDFG,
        cfg: ControlFlowRegion,
        dfg: StateSubgraphView,
        state_id: int,
        node: nodes.AccessNode,
        nodedesc: data.Data,
        global_stream: CodeIOStream,
        declaration_stream: CodeIOStream,
        allocation_stream: CodeIOStream,
    ) -> None:
        name = node.data
        if self.dispatcher.defined_vars.has(name):
            return
        if not isinstance(nodedesc, data.Array) or isinstance(nodedesc, data.View):
            raise TypeError(f"{name}: SoftHier storage holds arrays only, got {type(nodedesc).__name__}")
        ctype = nodedesc.dtype.ctype
        size = static_size(nodedesc, name)
        if nodedesc.storage == TCDM:
            symbol = tcdm_symbol(sdfg, name)
            if symbol not in self.statics:
                self.statics.add(symbol)
                self.globals.write(f'static {ctype} {symbol}[{size}] __attribute__((section(".l1"), aligned(64)));')
            declaration_stream.write(f"{ctype}* {name} = {symbol};", cfg, state_id, node)
            self.dispatcher.defined_vars.add(name, DefinedType.Pointer, f"{ctype} *")
            return
        # A transient HBM array: one object in .hbm, defined here
        if name not in self.statics:
            self.statics.add(name)
            self.globals.write(f'{ctype} {name}[{size}] __attribute__((section(".hbm"), aligned(64)));')
        self.dispatcher.defined_vars.add(name, DefinedType.Pointer, f"{ctype} *")

    def deallocate_array(  # pyright: ignore[reportIncompatibleMethodOverride] -- DaCe's annotation
        self,
        sdfg: SDFG,
        cfg: ControlFlowRegion,
        dfg: StateSubgraphView,
        state_id: int,
        node: nodes.AccessNode,
        nodedesc: data.Data,
        function_stream: CodeIOStream,
        callsite_stream: CodeIOStream,
    ) -> None:
        return

    # Copies: only the accesses of code nodes (pointer and value definitions) are generated; a copy between two
    # arrays must be a copy node by now

    def copy_memory(
        self,
        sdfg: SDFG,
        cfg: ControlFlowRegion,
        dfg: StateSubgraphView,
        state_id: int,
        src_node: nodes.Node,
        dst_node: nodes.Node,
        edge: MultiConnectorEdge[Memlet],
        function_stream: CodeIOStream,
        callsite_stream: CodeIOStream,
    ) -> None:
        if isinstance(src_node, nodes.AccessNode) and isinstance(dst_node, nodes.AccessNode):
            raise LoweringError(
                f"SoftHier: the copy {src_node.data} -> {dst_node.data} has no copy node; run the lowering pipeline"
            )
        self.cpu.copy_memory(sdfg, cfg, dfg, state_id, src_node, dst_node, edge, function_stream, callsite_stream)  # pyright: ignore[reportOptionalMemberAccess] -- DaCe's annotation
