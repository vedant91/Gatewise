"""Gatewise MCP server (stdio). Deterministic tools only.
The connected AI (your Claude/Cursor/...) proposes patches; this server accepts or rejects them.
No LLM and no API key live in here. The server never edits your repo: accepted diffs are returned for YOU to apply."""
import ast, logging, os, shutil

from mcp.server.fastmcp import FastMCP

from . import cli, core

mcp = FastMCP("gatewise")
logging.getLogger("httpx").setLevel(logging.WARNING)  # ~700 probe requests per scan; per-request rich logging made it crawl
CFG = core.load_config()
S = {"tree": None, "accepted": [], "last": None}  # session: a throw-away copy that accumulates accepted patches


def _tree():
    if S["tree"] is None:
        S["tree"] = core.make_tree(os.path.join(core.ROOT, "portal"))
    return S["tree"]


def _slim(R):
    return {k: v for k, v in R.items() if k not in ("before", "after", "tree_after")}


@mcp.tool()
def gatewise_scan() -> dict:
    """Build the who-can-open-what matrix on a local replica and list every leak (expected DENY, observed ALLOW).
    Each leak is proven with a canary or hash match, never a bare 200. Also writes a failing pytest to artifacts/."""
    with core.replica(_tree()) as base:
        res = core.scan(base, CFG)
    L = core.leaks(res["cells"])
    path = cli.save("test_exploit.py", core.exploit_source(res["cells"]))
    return {"leaks": len(L), "by_action": core.summary(res["cells"]), "exploit_test": path,
            "sample": [f"{c['user']} can read d{c['doc']} via {c['action']}" for c in L[:25]]}


@mcp.tool()
def gatewise_locate() -> dict:
    """Return the functions that fetch a document without calling the existing authorization helper, with their
    source, so you can write the smallest guard-only patch. Reuse the helper named in 'helpers'."""
    pdir = os.path.join(_tree(), "portal")
    src = open(os.path.join(pdir, "app.py"), encoding="utf-8").read()
    segs = {n.name: ast.get_source_segment(src, n) for n in ast.parse(src).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out = core.locate(pdir)
    for f in out["findings"]:
        f["source"] = segs.get(f["function"])
    out["helper_source"] = {h: segs[h] for h in out["helpers"] if h in segs}
    out["rules"] = {"file": CFG["allowed_files"], "max_changed_lines": CFG["max_changed_lines"],
                    "diff_format": "unified diff, paths a/portal/app.py and b/portal/app.py"}
    return out


@mcp.tool()
def gatewise_verify_patch(diff: str, mutation_check: bool = False) -> dict:
    """Judge a unified diff. ACCEPTED only if: the patch applies, it is guard-only and small, the exploit test makes
    progress, ONLY leak cells flipped (zero collateral), recorded normal responses are identical and the portal's
    legit-flow tests pass. On REJECTED, 'collateral' and 'reasons' name the exact cells to fix; revise and call again.
    Accepted patches stack in this session, so send one flaw at a time."""
    R = core.verify_patch(_tree(), diff, CFG, mutants=mutation_check)
    if R.get("tree_after"):
        shutil.rmtree(S["tree"], ignore_errors=True)
        S["tree"] = R["tree_after"]
        S["accepted"].append(diff)
    if "before" in R:
        S["last"] = (R, diff)
    return _slim(R)


@mcp.tool()
def gatewise_report() -> dict:
    """Current state of the session: leaks still open on the patched replica, accepted diffs (apply these to your
    repo yourself, one commit each) and the path of the latest certificate."""
    with core.replica(_tree()) as base:
        res = core.scan(base, CFG)
    cert = cli.save("certificate_session.html", core.certificate(S["last"][0], S["last"][1], CFG)) if S["last"] else None
    return {"leaks_remaining": len(core.leaks(res["cells"])), "regressions": sum(core.kind(c) == "REGRESSION" for c in res["cells"]),
            "accepted_diffs": S["accepted"], "certificate": cert,
            "scope": "fixed on a local replica for the tested matrix; a human reviews and merges"}


@mcp.tool()
def gatewise_reset() -> str:
    """Throw away the session copy and all accepted patches."""
    shutil.rmtree(S["tree"] or "", ignore_errors=True)
    S.update(tree=None, accepted=[], last=None)
    return "session reset"


@mcp.prompt()
def fix_idor() -> str:
    """Loop that turns Gatewise into a verified-fix workflow using the user's own AI."""
    return ("Fix broken access control with Gatewise.\n"
            "1. Call gatewise_scan and read the leaks.\n2. Call gatewise_locate for the vulnerable functions and the existing helper.\n"
            "3. Write ONE small unified diff for ONE flaw: add a guard that calls the existing helper. Do not rename, reformat, "
            "change signatures or add dependencies.\n4. Call gatewise_verify_patch. If REJECTED, read 'collateral' and 'reasons', "
            "fix exactly those cells, retry (max 3 times per flaw).\n5. Repeat until gatewise_report shows leaks_remaining = 0.\n"
            "6. Apply the accepted diffs to the repo as separate commits and open a PR for a human to review.")


if __name__ == "__main__":
    mcp.run()
