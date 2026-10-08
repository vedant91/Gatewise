"""Engine self-checks: the verifier must catch the obvious bad fix and accept the policy-aware one."""
import asyncio, json, os, shutil, sys

import pytest

from gatewise import core

ROOT = core.ROOT
CFG = core.load_config()


def patch(name):
    return open(os.path.join(ROOT, "examples", "patches", name), encoding="utf-8").read()


@pytest.fixture(scope="module")
def tree():
    t = core.make_tree(os.path.join(ROOT, "portal"))
    yield t
    shutil.rmtree(t, ignore_errors=True)


@pytest.fixture(scope="module")
def before(tree):
    with core.replica(tree) as base:
        return core.scan(base, CFG)


def test_exact_read_leaks(before):
    got = {(c["user"], c["doc"]) for c in core.leaks(before["cells"]) if c["action"] == "read"}
    assert got == {("bob", 1), ("dave", 1), ("dave", 2), ("alice", 3), ("dave", 3),
                   ("bob", 4), ("alice", 6), ("bob", 6), ("dave", 6)}


def test_total_leaks_and_no_regressions(before):
    assert len(core.leaks(before["cells"])) == 74
    assert not [c for c in before["cells"] if core.kind(c) == "REGRESSION"]


def test_scope_lock_refuses_other_hosts():
    with pytest.raises(PermissionError):
        core.client("http://example.com", CFG).get("/")


def test_naive_patch_rejected_with_shared_doc_collateral(tree):
    R = core.verify_patch(tree, patch("naive.diff"), CFG, mutants=True)
    assert R["verdict"] == "REJECTED"
    assert "bob/d2/read ALLOW->DENY" in R["collateral"]
    assert R["gates"]["mutation_sanity"], R.get("mutants")  # verifier catches no-op and deny-all mutants


def test_policy_aware_patch_accepted(tree):
    R = core.verify_patch(tree, patch("smart_1_read.diff"), CFG, mutants=False)
    try:
        assert R["verdict"] == "ACCEPTED" and R["collateral"] == [] and len(R["closed"]) == 9
    finally:
        shutil.rmtree(R.get("tree_after", ""), ignore_errors=True)


def test_guard_only_gate_blocks_signature_change(tree):
    new = core.make_tree(os.path.join(tree, "portal"))
    p = os.path.join(new, "portal", "app.py")
    s = open(p, encoding="utf-8").read().replace("def search(q_:", "def search(query:", 1)
    open(p, "w", encoding="utf-8").write(s)
    try:
        assert any("signature" in e for e in core.ast_gate(tree, new, CFG))
    finally:
        shutil.rmtree(new, ignore_errors=True)


def test_line_cap_and_file_allowlist():
    big = "--- a/portal/app.py\n+++ b/portal/app.py\n@@ -1 +1 @@\n" + "".join(f"+x{i}\n" for i in range(30))
    assert any("cap" in e for e in core.constraints(big, CFG)[0])
    other = "--- a/portal/tests/test_legit.py\n+++ b/portal/tests/test_legit.py\n@@ -1 +1 @@\n+x\n"
    assert any("touches" in e for e in core.constraints(other, CFG)[0])


def test_mcp_roundtrip():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    def data(res):
        return res.structuredContent or json.loads(res.content[0].text)

    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "gatewise.mcp_server"], cwd=ROOT)
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = {t.name for t in (await s.list_tools()).tools}
                bad = data(await s.call_tool("gatewise_verify_patch", {"diff": patch("naive.diff")}))
                good = data(await s.call_tool("gatewise_verify_patch", {"diff": patch("smart_1_read.diff")}))
                rep = data(await s.call_tool("gatewise_report", {}))
                await s.call_tool("gatewise_reset", {})
                return names, bad, good, rep

    names, bad, good, rep = asyncio.run(go())
    assert {"gatewise_scan", "gatewise_locate", "gatewise_verify_patch", "gatewise_report"} <= names
    assert bad["verdict"] == "REJECTED" and good["verdict"] == "ACCEPTED"
    assert rep["leaks_remaining"] == 65 and len(rep["accepted_diffs"]) == 1
