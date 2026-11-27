"""Self-check of run_agent.call: shared reads, folder writes, refusals, per study (python agents/test_run_agent.py)."""

import os
import pathlib
import tempfile

import run_agent as r

out = pathlib.Path(tempfile.mkdtemp())
assert "tsvc_2_va" in r.call("read_file", {"path": "agents/tasks.json"}, out)[0]
assert r.call("write_file", {"path": "compute.cpp", "content": "x"}, out)[0] == "wrote compute.cpp"
assert r.call("write_file", {"path": "../escape", "content": "x"}, out)[0].startswith("error")
assert r.call("read_file", {"path": "/etc/passwd"}, out)[0].startswith("error")
assert r.call("list_files", {}, out)[0] == "compute.cpp"
assert r.call("finish", {"summary": "s"}, out) == ("done", True)
r.STUDY = r.STUDIES["softhier"]
assert "gemm64" in r.call("read_file", {"path": "tasks.json"}, out)[0]
assert "alloy_kernel" in r.call("read_file", {"path": "SPEC.md"}, out)[0]
prior_image = os.environ.pop("SOFTHIER_IMAGE", None)
assert "run" not in {t["function"]["name"] for t in r.tools_for("softhier", "tool")}
os.environ["SOFTHIER_IMAGE"] = "/tmp/softhier-v1.sif"
assert "run" in {t["function"]["name"] for t in r.tools_for("softhier", "tool")}
if prior_image is None:
    os.environ.pop("SOFTHIER_IMAGE", None)
else:
    os.environ["SOFTHIER_IMAGE"] = prior_image
print("ok")
