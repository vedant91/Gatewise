"""Gatewise core: scope lock, access matrix, proof, locate, verify. Deterministic. No LLM in here."""
import ast, hashlib, html, json, os, re, shutil, socket, subprocess, sys, tempfile, time
from contextlib import contextmanager

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORE = shutil.ignore_patterns("__pycache__", "*.db", "uploads", ".pytest_cache")


def load_config(path=None):
    with open(path or os.path.join(ROOT, "gatewise.json")) as f:
        return json.load(f)


# ---------- scope lock + sessions ----------
class ScopedTransport(httpx.HTTPTransport):
    """Refuses any host that is not on the allowlist. Every request in this engine goes through it."""

    def __init__(self, allow_hosts, **kw):
        super().__init__(**kw)
        self.allow = set(allow_hosts)

    def handle_request(self, request):
        if request.url.host not in self.allow:
            raise PermissionError(f"scope-lock: {request.url.host} is not on the allowlist")
        return super().handle_request(request)


def client(base, cfg, user=None):
    c = httpx.Client(base_url=base, transport=ScopedTransport(cfg["allow_hosts"]), timeout=10)
    if user and user != "anon":
        c.post("/login", json={"name": user, "password": cfg["accounts"][user]}).raise_for_status()
    return c


def sha(b):
    return hashlib.sha256(b).hexdigest()


def norm(text, cfg):
    """Normalise a response so volatile fields (tokens, timestamps) do not look like changes."""
    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in sorted(x.items()) if k.lower() not in cfg["volatile_keys"]}
        return [strip(v) for v in x] if isinstance(x, list) else x
    try:
        return json.dumps(strip(json.loads(text)), sort_keys=True)
    except ValueError:
        return text


# ---------- the access matrix ----------
def key(c):
    return (c["user"], c["doc"], c["action"])


def fmt(k):
    return f"{k[0]}/d{k[1]}/{k[2]}"


def kind(c):
    if c["expected"] == "DENY" and c["observed"] == "ALLOW":
        return "LEAK"
    if c["expected"] == "ALLOW" and c["observed"] == "DENY":
        return "REGRESSION"
    return None


def leaks(cells):
    return [c for c in cells if kind(c) == "LEAK"]


def _cell(cfg, u, d, a, exp, ok, r, path, proof, canary, h):
    return {"user": u, "doc": d, "action": a, "expected": "ALLOW" if exp else "DENY",
            "observed": "ALLOW" if ok else "DENY", "status": r.status_code,
            "sig": sha((str(r.status_code) + "|" + norm(r.text, cfg)).encode()),
            "path": path, "proof": proof, "canary": canary, "hash": h, "pw": cfg["accounts"].get(u)}


def scan(base, cfg, ref=None):
    """Expected matrix (from each account's own list views) vs observed matrix (what the server really does).
    ref = baselines (canaries, hashes) learned from the UNPATCHED build; a patched build must never redefine them."""
    users = list(cfg["accounts"])
    who = users + ["anon"]
    cl = {u: client(base, cfg, u) for u in who}
    try:
        views, titles = {u: set() for u in users}, {}
        for u in users:
            for v in cfg["views"]:
                r = cl[u].get(v)
                if r.status_code == 200:
                    for d in r.json()["documents"]:
                        views[u].add(d["id"])
                        titles[d["id"]] = d["title"]
        docs, orc = sorted(titles), cfg["oracle_user"]
        tok = {d: re.search(r"TITLE-[\w-]+", titles[d]).group(0) for d in docs}
        if ref is None:
            canary = {}
            for d in docs:
                m = re.search(r"CANARY-[\w-]+", cl[orc].get(cfg["endpoints"]["read"].format(id=d)).text)
                if not m:
                    raise RuntimeError(f"oracle account '{orc}' cannot read d{d}: cannot learn its canary")
                canary[d] = m.group(0)
            hashes = {(a, d): sha(cl[orc].get(tpl.format(id=d, q=tok[d])).content)
                      for a, tpl in cfg["endpoints"].items() for d in docs}
        else:
            canary, hashes = ref["canary"], ref["hashes"]
        cells = []
        for a, tpl in cfg["endpoints"].items():
            for d in docs:
                path = tpl.format(id=d, q=tok[d])
                h = hashes[a, d]
                for u in who:
                    r = cl[u].get(path)
                    if a == "search":
                        ok, proof, can = r.status_code == 200 and tok[d] in r.text, "canary", tok[d]
                    elif a in cfg["hash_actions"]:
                        ok, proof, can = r.status_code == 200 and sha(r.content) == h, "hash", canary[d]
                    else:
                        ok, proof, can = r.status_code == 200 and canary[d] in r.text, "canary", canary[d]
                    cells.append(_cell(cfg, u, d, a, d in views.get(u, ()), ok, r, path, proof, can, h))
        for tc in cfg["token_cases"]:
            owner, d = tc["owner"], tc["doc"]
            share = cfg["share_path"].format(doc=d)
            t = cl[owner].post(share, json=tc["json"]).json()["token"]
            path = cfg["token_path"].format(token=t)
            for u in who:
                if u in (owner, orc):
                    continue
                r = cl[u].get(path)
                c = _cell(cfg, u, d, tc["name"], u in tc["allow"], r.status_code == 200 and canary[d] in r.text,
                          r, cfg["token_path"], "canary", canary[d], None)
                c["setup"] = {"owner": owner, "pw": cfg["accounts"][owner], "path": share, "json": tc["json"]}
                cells.append(c)
        return {"cells": cells, "docs": docs, "titles": titles, "ref": {"canary": canary, "hashes": hashes}}
    finally:
        for c in cl.values():
            c.close()


def judge(before, after, unstable=()):
    """Blast-radius check: only leak cells may flip. Anything else that moved is collateral."""
    B = {key(c): c for c in before["cells"]}
    A = {key(c): c for c in after["cells"]}
    closed, collateral, new_leaks = [], [], []
    for k, b in B.items():
        a = A.get(k)
        if a is None:
            collateral.append((k, "cell missing"))
            continue
        if b["observed"] != a["observed"]:
            if kind(b) == "LEAK" and a["observed"] == "DENY":
                closed.append(k)
            else:
                collateral.append((k, f"{b['observed']}->{a['observed']}"))
        elif b["observed"] == "ALLOW" and kind(b) is None and k not in unstable and b["sig"] != a["sig"]:
            collateral.append((k, "response changed"))
        if kind(a) == "LEAK" and kind(b) != "LEAK":
            new_leaks.append(k)
    return {"closed": closed, "collateral": collateral, "new_leaks": new_leaks,
            "remaining": [k for k, a in A.items() if kind(a) == "LEAK"]}


def summary(cells):
    out = {}
    for c in cells:
        s = out.setdefault(c["action"], {"cells": 0, "leaks": 0, "regressions": 0})
        s["cells"] += 1
        s["leaks"] += kind(c) == "LEAK"
        s["regressions"] += kind(c) == "REGRESSION"
    return out


# ---------- proof: exploit as a failing test ----------
EXPLOIT = '''"""Generated by Gatewise. RED while the leak exists, GREEN once fixed. Keep it: it is your regression guard."""
import hashlib, json, os
import httpx
import pytest

BASE = os.environ["TARGET"]
LEAKS = json.loads(r\'\'\'__LEAKS__\'\'\')


_CLIENTS = {}


def who(name, pw):
    if name not in _CLIENTS:
        c = httpx.Client(base_url=BASE)
        if name != "anon":
            assert c.post("/login", json={"name": name, "password": pw}).status_code == 200
        _CLIENTS[name] = c
    return _CLIENTS[name]


@pytest.mark.parametrize("L", LEAKS, ids=lambda L: "%s-d%s-%s" % (L["user"], L["doc"], L["action"]))
def test_no_leak(L):
    path = L["path"]
    if L.get("setup"):
        s = L["setup"]
        token = who(s["owner"], s["pw"]).post(s["path"], json=s["json"]).json()["token"]
        path = path.format(token=token)
    r = who(L["user"], L["pw"]).get(path)
    if L["proof"] == "hash":
        leaked = r.status_code == 200 and hashlib.sha256(r.content).hexdigest() == L["hash"]
    else:
        leaked = r.status_code == 200 and L["canary"] in r.text
    assert not leaked, "%s can read d%s via %s" % (L["user"], L["doc"], L["action"])
'''


def exploit_source(cells):
    keep = ("user", "doc", "action", "path", "proof", "canary", "hash", "pw", "setup")
    return EXPLOIT.replace("__LEAKS__", json.dumps([{k: c.get(k) for k in keep} for c in leaks(cells)]))


def run_exploit(src, base):
    d = tempfile.mkdtemp(prefix="gw-exp-")
    p = os.path.join(d, "test_exploit.py")
    with open(p, "w") as f:
        f.write(src)
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", p, "-q", "--tb=no", "-p", "no:cacheprovider"],
                           env=dict(os.environ, TARGET=base), capture_output=True, text=True, stdin=subprocess.DEVNULL)
        m = re.search(r"(\d+) failed", r.stdout)
        return int(m.group(1)) if m else 0, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------- locate: which function forgot the check ----------
def _calls(fn):
    return {n.func.id if isinstance(n.func, ast.Name) else n.func.attr
            for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}


def locate(portal_dir):
    """ponytail: heuristic rules for this lab app; Semgrep rules are the upgrade path for other codebases."""
    tree = ast.parse(open(os.path.join(portal_dir, "app.py")).read())
    helpers = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith(("can_", "authorize", "require_"))]
    out = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            route = None
            for d in n.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and getattr(d.func.value, "id", "") == "app"
                        and d.args and isinstance(d.args[0], ast.Constant)):
                    route = (d.func.attr.upper(), d.args[0].value)
            if not route:
                continue
            calls = _calls(n)
            sql = " ".join(c.value.lower() for c in ast.walk(n) if isinstance(c, ast.Constant) and isinstance(c.value, str))
            guarded = bool(set(helpers) & calls)
            why = k = None
            if "get_document" in calls and not guarded:
                why, k = "fetches an object by id and never calls an authorization helper", "getter"
            elif " like " in sql and not guarded:
                why, k = "searches documents with no per-user filter", "query"
            if why:
                out.append({"function": n.name, "method": route[0], "path": route[1], "line": n.lineno,
                            "body_line": n.body[0].lineno, "col": n.body[0].col_offset, "reason": why, "kind": k})
        elif (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and getattr(n.value.func, "attr", "") == "mount"
              and any(isinstance(a, ast.Call) and getattr(a.func, "id", "") == "StaticFiles" for a in n.value.args)):
            out.append({"function": "(static mount)", "method": "GET", "path": n.value.args[0].value, "line": n.lineno,
                        "reason": "static mount serves files with no authorization", "kind": "mount"})
    return {"helpers": helpers, "findings": out}


# ---------- replica: a throw-away copy of the app, never the live site ----------
def make_tree(src):
    d = tempfile.mkdtemp(prefix="gw-")
    shutil.copytree(src, os.path.join(d, "portal"), ignore=IGNORE)
    return d


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@contextmanager
def replica(tree):
    port, data = _free_port(), tempfile.mkdtemp(prefix="gw-data-")
    env = dict(os.environ, PORTAL_DB=os.path.join(data, "p.db"), PORTAL_UPLOADS=os.path.join(data, "up"))
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--app-dir", os.path.join(tree, "portal"),
                          "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
                         env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                httpx.get(base + "/public", timeout=1)
                break
            except httpx.HTTPError:
                if p.poll() is not None:
                    raise RuntimeError("replica failed to boot: " + p.stderr.read().decode()[-400:])
                time.sleep(0.15)
        else:
            p.terminate()
            raise RuntimeError("replica did not start: " + p.communicate(timeout=5)[1].decode(errors="replace")[-500:])
        yield base
    finally:
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
        shutil.rmtree(data, ignore_errors=True)


def apply_diff(tree, diff):
    p = os.path.join(tree, "_patch.diff")
    with open(p, "w", newline="\n") as f:
        f.write(diff if diff.endswith("\n") else diff + "\n")
    r = subprocess.run(["git", "apply", "--whitespace=nowarn", p], cwd=tree, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    os.remove(p)
    return r.returncode == 0, r.stderr.strip()


# ---------- gates that look at the diff itself ----------
def constraints(diff, cfg):
    errs, files = [], re.findall(r"^\+\+\+ b/(\S+)", diff, re.M)
    if not files:
        errs.append("empty or invalid diff")
    errs += [f"touches {f} (allowed: {cfg['allowed_files']})" for f in files if f not in cfg["allowed_files"]]
    n = sum(1 for l in diff.splitlines() if l and l[0] in "+-" and not l.startswith(("+++", "---")))
    if n > cfg["max_changed_lines"]:
        errs.append(f"{n} changed lines > cap {cfg['max_changed_lines']}")
    return errs, n


def _imports(n):
    if isinstance(n, ast.Import):
        return [a.name.split(".")[0] for a in n.names]
    if isinstance(n, ast.ImportFrom) and n.module and not n.level:
        return [n.module.split(".")[0]]
    return []


def ast_gate(old, new, cfg):
    """Guard-only: nothing removed, no signature/route changes, no new dependencies, file still parses."""
    errs = []
    for f in cfg["allowed_files"]:
        po, pn = os.path.join(old, f), os.path.join(new, f)
        if not (os.path.exists(po) and os.path.exists(pn)):
            continue
        try:
            to, tn = ast.parse(open(po).read()), ast.parse(open(pn).read())
        except SyntaxError as e:
            errs.append(f"{f}: patched file does not parse ({e.msg})")
            continue
        sig = lambda t: {n.name: (ast.dump(n.args), [ast.dump(d) for d in n.decorator_list])
                         for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        a, b = sig(to), sig(tn)
        for name, s in a.items():
            if name not in b:
                errs.append(f"function {name} was removed")
            elif b[name] != s:
                errs.append(f"function {name}: signature or route decorator changed")
        known = {m for n in ast.walk(to) for m in _imports(n)}
        errs += [f"new dependency {m}" for n in ast.walk(tn) for m in _imports(n)
                 if m not in sys.stdlib_module_names and m not in known]
    return errs


# ---------- mutants: prove the verifier has teeth ----------
def deny_all_mutant(tree):
    d = make_tree(os.path.join(tree, "portal"))
    path = os.path.join(d, "portal", "app.py")
    lines = open(path).read().split("\n")
    for f in sorted((f for f in locate(os.path.join(d, "portal"))["findings"] if f["kind"] == "getter"),
                    key=lambda f: -f["body_line"]):
        lines.insert(f["body_line"] - 1, " " * f["col"] + "raise HTTPException(403)")
    open(path, "w").write("\n".join(lines))
    return d


def mutation_sanity(tree, before, unstable, cfg):
    noop_rejected = not judge(before, before, unstable)["closed"]  # revert / allow-all: closes nothing
    d = deny_all_mutant(tree)
    try:
        with replica(d) as base:
            after = scan(base, cfg, before["ref"])
    finally:
        shutil.rmtree(d, ignore_errors=True)
    j = judge(before, after, unstable)
    return {"noop_rejected": noop_rejected, "deny_all_rejected": bool(j["collateral"])}


def run_legit_tests(tree):
    r = subprocess.run([sys.executable, "-m", "pytest", os.path.join(tree, "portal", "tests"), "-q", "--tb=line",
                        "-p", "no:cacheprovider"], env=dict(os.environ, PORTAL_DIR=os.path.join(tree, "portal")),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1]


# ---------- the verifier ----------
def verify_patch(tree, diff, cfg, mutants=True):
    """Deterministic accept/reject. The AI never decides. On accept, R['tree_after'] holds the patched copy."""
    R = {"gates": {}, "closed": [], "collateral": [], "new_leaks": [], "reasons": [], "accepted": False}
    with replica(tree) as base:
        before = scan(base, cfg)
        again = scan(base, cfg)
        unstable = {key(a) for a, b in zip(before["cells"], again["cells"]) if a["sig"] != b["sig"]}
        src = exploit_source(before["cells"])
        failed_before, _ = run_exploit(src, base)
    R["leaks_before"] = len(leaks(before["cells"]))
    R["gates"]["exploit_red_on_replica"] = failed_before > 0
    if not failed_before:
        R["verdict"] = "UNVERIFIED"
        R["reasons"].append("exploit test is not RED on the unpatched replica: the replica does not reproduce a leak")
        return R
    errs, R["lines"] = constraints(diff, cfg)
    t2 = make_tree(os.path.join(tree, "portal"))
    try:
        ok, msg = apply_diff(t2, diff)
        R["gates"]["patch_applies"] = ok
        if not ok:
            R["verdict"] = "REJECTED"
            R["reasons"].append("patch does not apply: " + msg)
            return R
        errs += ast_gate(tree, t2, cfg)
        R["gates"]["guard_only_constraints"] = not errs
        R["reasons"] += errs
        with replica(t2) as base2:
            after = scan(base2, cfg, before["ref"])
            failed_after, _ = run_exploit(src, base2)
        j = judge(before, after, unstable)
        flips = [c for c in j["collateral"] if c[1] != "response changed"]
        R["closed"], R["new_leaks"] = [fmt(k) for k in j["closed"]], [fmt(k) for k in j["new_leaks"]]
        R["collateral"] = [f"{fmt(k)} {why}" for k, why in j["collateral"]]
        R["remaining"] = len(j["remaining"])
        R["gates"]["exploit_progress"] = failed_after < failed_before
        R["gates"]["blast_radius_only_leaks_flipped"] = not flips and not j["new_leaks"] and bool(j["closed"])
        R["gates"]["golden_flows_identical"] = not [c for c in j["collateral"] if c[1] == "response changed"]
        R["gates"]["legit_tests_pass"], legit = run_legit_tests(t2)
        if not R["gates"]["legit_tests_pass"]:
            R["reasons"].append("portal legit-flow tests failed: " + legit)
        if mutants:
            m = mutation_sanity(tree, before, unstable, cfg)
            R["mutants"] = m
            R["gates"]["mutation_sanity"] = all(m.values())
        if flips:
            R["reasons"].append("legitimate access changed: " + ", ".join(fmt(k) for k, _ in flips[:6]) + (" ..." if len(flips) > 6 else ""))
        R["accepted"] = all(R["gates"].values())
        R["verdict"] = "ACCEPTED" if R["accepted"] else "REJECTED"
        R["before"], R["after"] = before, after
        if R["accepted"]:
            R["tree_after"] = t2
        return R
    finally:
        if not R["accepted"]:
            shutil.rmtree(t2, ignore_errors=True)


# ---------- certificate ----------
def _grid(res, cfg, action):
    users = list(cfg["accounts"]) + ["anon"]
    cells = {key(c): c for c in res["cells"]}
    rows = ""
    for d in res["docs"]:
        tds = ""
        for u in users:
            c = cells.get((u, d, action))
            k = kind(c) if c else None
            cls = "leak" if k == "LEAK" else "reg" if k == "REGRESSION" else "ok"
            tds += f'<td class="{cls}">{"✓" if c and c["observed"] == "ALLOW" else "✕"}</td>'
        rows += f"<tr><th>d{d}</th>{tds}</tr>"
    return "<table><tr><th></th>" + "".join(f"<th>{u}</th>" for u in users) + "</tr>" + rows + "</table>"


def certificate(R, diff, cfg):
    gates = "".join(f"<tr><td>{g}</td><td class=\"{'ok' if v else 'leak'}\">{'PASS' if v else 'FAIL'}</td></tr>" for g, v in R["gates"].items())
    li = lambda xs: "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in xs) + "</ul>" if xs else "<p>none</p>"
    return f"""<!doctype html><meta charset="utf-8"><title>Gatewise certificate</title>
<style>body{{font:15px system-ui;max-width:900px;margin:24px auto;padding:0 16px}}table{{border-collapse:collapse;margin:8px 0}}
td,th{{border:1px solid #ccc;padding:5px 10px;text-align:center}}.ok{{background:#dcfce7}}.leak{{background:#fee2e2}}.reg{{background:#fef3c7}}
pre{{background:#0f172a;color:#e2e8f0;padding:12px;overflow:auto}}.v{{font-size:1.4rem;font-weight:700}}</style>
<h1>Gatewise Verified-Fix Certificate</h1><p class="v">{R['verdict']}</p>
<p>Leaks before: <b>{R['leaks_before']}</b> · closed by this patch: <b>{len(R['closed'])}</b> · still open: <b>{R.get('remaining', '?')}</b>
· collateral changes: <b>{len(R['collateral'])}</b> · changed lines: <b>{R.get('lines', '?')}</b></p>
<h2>Gates</h2><table>{gates}</table>
<h2>Problems found</h2>{li(R['reasons'])}
<h2>Collateral (legit access that changed)</h2>{li(R['collateral'])}
<h2>Matrix, action "read": before / after</h2>{_grid(R['before'], cfg, 'read') if 'before' in R else ''}{_grid(R['after'], cfg, 'read') if 'after' in R else ''}
<p>✕/✓ = what the server does. Red = leak, amber = legitimate user locked out.</p>
<h2>Diff</h2><pre>{html.escape(diff)}</pre>
<p><i>Scope: fixed on a local replica for the tested user × document × action matrix. This does not prove no other flaws exist.
A human reviews and merges.</i></p>"""
