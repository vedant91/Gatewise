"""Build site/demo-data.js and site/assets from recorded MCP flows (artifacts/flow_<app>.json) plus real browser
screenshots of each demo app's UI, before and after the fix.
Run:  python site/build_data.py [path-to-gatewise-vulnerable-apps]"""
import glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from gatewise import core  # noqa: E402

APPS = {
    "docvault": {"name": "DocVault", "blurb": "Document sharing for companies", "who": "ben", "item": "/documents/1",
                 "story": "ben is a marketing manager at Acme Industries and is not on the Payroll project. He opens the CFO's Q1 payroll register, with executive salaries and a bank reference."},
    "paydesk": {"name": "PayDesk", "blurb": "A payroll portal", "who": "omar", "item": "/payslips/1",
                "story": "omar is an operations analyst at Acme Industries. He opens his colleague Lena Fischer's payslip, with her salary, bank details and confidential HR notes."},
}
PRE = {  # what the AI says before each tool call; the replies after each call are the real tool output
    "sandbox": "First I will build a sandbox: I copy your code, start it on localhost with fake data and check that it boots. Nothing touches production.",
    "scan": "Now I will log in as every test account and try every item through every door, to see who can reach what they should not.",
    "explain": "Let me read the code and explain, in plain words, why this app is vulnerable.",
    "proof": "I will replay the leaks in a real browser inside the sandbox, so you can see them instead of only reading about them.",
    "patch": "Now I fix it one flaw at a time. Every patch goes to the verifier, which judges it with fixed rules.",
    "after": "Let me test everything again, and replay the same browser requests after the fix.",
    "pr": "Last step: I package the fixes as a pull request with a before and after report, for you to review.",
}


def capture_ui(app, repo, outdir):
    """Real screenshots of the app's own web UI: login, dashboard, the flaw in action, and the same URL after the fix."""
    from playwright.sync_api import sync_playwright
    cfg = core.load_config(os.path.join(repo, app, "gatewise.json"))
    t0, t1 = core.make_tree(core.app_src(cfg), cfg), core.make_tree(core.app_src(cfg), cfg)
    try:
        for p in sorted(glob.glob(os.path.join(ROOT, "examples", "vuln_apps_patches", app, "smart_*.diff"))):
            ok, msg = core.apply_diff(t1, open(p, encoding="utf-8").read())
            assert ok, msg
        who, item = APPS[app]["who"], APPS[app]["item"]
        with core.replica(t0, cfg) as b0, core.replica(t1, cfg) as b1, sync_playwright() as pw:
            br = pw.chromium.launch()

            def shot(base, path, name, user=None):
                ctx = br.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1.25)
                pg = ctx.new_page()
                if user:
                    pg.goto(base + "/login")
                    pg.fill("#u", user)
                    pg.fill("#p", "pw-" + user)
                    pg.click("#signin")
                    pg.wait_for_url(lambda u: not u.endswith("/login"))
                pg.goto(base + path)
                pg.wait_for_timeout(700)
                pg.screenshot(path=os.path.join(outdir, name))
                ctx.close()

            shot(b0, "/login", "ui_login.png")
            shot(b0, "/", "ui_dashboard.png", who)
            shot(b0, "/documents" if app == "docvault" else "/payslips", "ui_list.png", who)
            shot(b0, item, "ui_leak.png", who)
            shot(b1, item, "ui_blocked.png", who)
            br.close()
    finally:
        shutil.rmtree(t0, ignore_errors=True)
        shutil.rmtree(t1, ignore_errors=True)


def build_app(app, repo):
    out = os.path.join(HERE, "assets", app)
    os.makedirs(out, exist_ok=True)
    capture_ui(app, repo, out)
    log = json.load(open(os.path.join(ROOT, "artifacts", f"flow_{app}.json"), encoding="utf-8"))
    by = lambda tool, action=None: [e for e in log if e["tool"] == tool and (action is None or e["args"].get("action") == action)]
    start, scans, locate, explain = by("gatewise_sandbox", "start")[0]["result"], by("gatewise_investigate", "scan"), by("gatewise_investigate", "locate")[0]["result"], by("gatewise_investigate", "explain")[0]["result"]
    vis, plans, verifies, pr = by("gatewise_prove"), [e["args"]["note"] for e in by("gatewise_fix", "plan")], by("gatewise_fix", "verify"), by("gatewise_deliver", "pull_request")[0]["result"]
    pat = os.path.join(ROOT, "examples", "vuln_apps_patches", app)
    diffs = [open(os.path.join(pat, "naive.diff"), encoding="utf-8").read()] + [open(f, encoding="utf-8").read() for f in sorted(glob.glob(os.path.join(pat, "smart_*.diff")))]
    shots = {}
    for side, v in (("before", vis[0]), ("after", vis[-1])):
        shots[side] = []
        for i, s in enumerate(v["result"]["steps"]):
            name = f"{side}_{i}.png"
            shutil.copy(s["shot"], os.path.join(out, name))
            shots[side].append({"user": s["user"], "doc": s["doc"], "action": s["action"], "verdict": s["verdict"], "request": s.get("request", ""), "file": f"assets/{app}/{name}"})
    shutil.copy(pr["report"]["path"], os.path.join(out, "report.html"))
    # the signed passport exactly as committed on the pull request branch, verified here against that branch
    from gatewise import passport as pp
    repo, branch = pr["pr"]["repo"], pr["pr"]["branch"]
    for name in ("passport.json", "passport.html"):
        raw = subprocess.run(["git", "show", f"{branch}:gatewise-report/{name}"], cwd=repo, capture_output=True, text=True, encoding="utf-8").stdout
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(raw)
    pj = json.load(open(os.path.join(out, "passport.json"), encoding="utf-8"))
    ver = pp.verify(os.path.join(out, "passport.json"), repo, branch)
    court = by("gatewise_fix", "court")[0]["result"]
    src = start["sandbox"]["source"]
    clone = pr["pr"]["repo"]
    clean = lambda t: t.replace(src, "your repository").replace(clone, "your repository")
    patches = []
    for e, d in zip(verifies, diffs):
        r = e["result"]
        patches.append({"title": e["args"].get("title", ""), "verdict": r["verdict"], "say": clean(r["say_to_user"]), "gates": r["gates"],
                        "closed": len(r["closed"]), "collateral": r["collateral"][:6], "lines": r.get("lines"),
                        "remaining": r.get("remaining"), "diff": d})
    return {
        "name": APPS[app]["name"], "blurb": APPS[app]["blurb"], "story": APPS[app]["story"], "who": APPS[app]["who"],
        "prompt": f"Use the gatewise tools on my repository, app {app}. Explain every step to me.",
        "pre": PRE, "ui": {k: f"assets/{app}/ui_{k}.png" for k in ("login", "dashboard", "list", "leak", "blocked")},
        "sandbox": {"say": clean(start["say_to_user"]), **{k: start["sandbox"][k] for k in ("files_copied", "endpoints", "endpoints_with_ids", "accounts")}},
        "scan": {"say": scans[0]["result"]["say_to_user"], "table": scans[0]["result"]["table"], "leaks": scans[0]["result"]["leaks"],
                 "checks": scans[0]["result"]["checks"], "by_action": scans[0]["result"]["by_action"]},
        "locate": {"say": clean(locate["say_to_user"]), "count": len(locate["findings"])},
        "explain": {"say": explain["say_to_user"], "table": explain["table"], "walkthrough": explain["walkthrough"], "fix": explain["fix_in_one_line"]},
        "shots": shots, "plans": plans, "patches": patches,
        "after": {"say": scans[-1]["result"]["say_to_user"], "checks": scans[-1]["result"]["checks"], "proof": vis[-1]["result"]["say_to_user"],
                  "before_proof": vis[0]["result"]["say_to_user"]},
        "court": {"sites": court["sites"], "attacks": court["attacks"], "caught": court["caught"], "survived": len(court["survived"]),
                  "results": [{k: r[k] for k in ("line", "mutant", "caught", "why")} for r in court["table_rows"]] if "table_rows" in court else
                             [{"line": ln, "mutant": mu, "caught": ca == "caught", "why": wh} for ln, mu, ca, wh in
                              (row for row in [[c.strip() for c in r.strip().strip("|").split("|")] for r in court["table"].split("\n")[2:]])]},
        "passport": {"status": ver["status"], "checks": ver["checks"], "claim": pj["claim"], "key_id": pj["attestation"]["key_id"], "digest": pj["attestation"]["digest"],
                     "code_commit": pj["subject"]["code_commit"], "tree": pj["subject"]["tree"], "diff_sha256": pj["subject"]["diff_sha256"],
                     "file": f"assets/{app}/passport.json", "page": f"assets/{app}/passport.html"},
        "graph": pr.get("knowledge_graph"),
        "pr": {"branch": pr["pr"]["branch"], "commits": pr["pr"]["commits"], "body": clean(pr["pr_description_markdown"]), "table": pr["table"],
               "checklist": pr["review_checklist"], "leaks_before": pr["leaks_before"], "leaks_after": pr["leaks_after"],
               "report": f"assets/{app}/report.html", "merge_link": pr.get("merge_link"),
               "say": re.sub(r" and also saved at file:///\S+\. ", ". ", pr["say_to_user"].replace(clone, "your repository"))},
    }


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "gatewise-vulnerable-apps")
    for app in APPS:  # clear only the per-app captures; assets/fonts is permanent
        shutil.rmtree(os.path.join(HERE, "assets", app), ignore_errors=True)
    data = {"apps": {app: build_app(app, repo) for app in APPS}}
    with open(os.path.join(HERE, "demo-data.js"), "w", encoding="utf-8") as f:
        f.write("window.DEMO = " + json.dumps(data, indent=1) + ";\n")
    print("wrote demo-data.js for", ", ".join(APPS), "| assets:", sum(len(fs) for _, _, fs in os.walk(os.path.join(HERE, "assets"))), "files")


if __name__ == "__main__":
    main()
