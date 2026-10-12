window.DEMO = {
 "apps": {
  "docvault": {
   "name": "DocVault",
   "blurb": "Document sharing for companies",
   "story": "ben is a marketing manager at Acme Industries and is not on the Payroll project. He opens the CFO's Q1 payroll register, with executive salaries and a bank reference.",
   "who": "ben",
   "prompt": "Use the gatewise tools on my repository, app docvault. Explain every step to me.",
   "pre": {
    "sandbox": "First I will build a sandbox: I copy your code, start it on localhost with fake data and check that it boots. Nothing touches production.",
    "scan": "Now I will log in as every test account and try every item through every door, to see who can reach what they should not.",
    "explain": "Let me read the code and explain, in plain words, why this app is vulnerable.",
    "proof": "I will replay the leaks in a real browser inside the sandbox, so you can see them instead of only reading about them.",
    "patch": "Now I fix it one flaw at a time. Every patch goes to the verifier, which judges it with fixed rules.",
    "after": "Let me test everything again, and replay the same browser requests after the fix.",
    "pr": "Last step: I package the fixes as a pull request with a before and after report, for you to review."
   },
   "ui": {
    "login": "assets/docvault/ui_login.png",
    "dashboard": "assets/docvault/ui_dashboard.png",
    "list": "assets/docvault/ui_list.png",
    "leak": "assets/docvault/ui_leak.png",
    "blocked": "assets/docvault/ui_blocked.png"
   },
   "sandbox": {
    "say": "I copied docvault from your repository into a throwaway sandbox and started it on a private localhost port with fake data. It exposes 13 endpoints (6 of them take an item id) and has 5 test accounts: ana (admin), ben (member), cara (viewer), gus (admin), hana (member). Nothing here touches your real site or real data. Next I will log in as each account and test who can open what.",
    "files_copied": 4,
    "endpoints": 13,
    "endpoints_with_ids": 6,
    "accounts": 5
   },
   "scan": {
    "say": "I logged in as 5 accounts, plus an anonymous visitor, and tried every item through 8 doors (opening it, downloading it, comments, search, share links, direct file URLs). 85 of 165 checks let someone reach something they should not. A leak only counts when a hidden canary string from another account's item shows up in the response.",
    "table": "| Door | Checks | Leaks |\n|---|---|---|\n| read | 30 | 14 |\n| original | 30 | 16 |\n| comments | 30 | 14 |\n| raw | 30 | 19 |\n| search | 30 | 14 |\n| token_org_only | 5 | 3 |\n| token_public | 5 | 0 |\n| token_expired | 5 | 5 |",
    "leaks": 85,
    "checks": 165,
    "by_action": {
     "read": {
      "cells": 30,
      "leaks": 14,
      "regressions": 0
     },
     "original": {
      "cells": 30,
      "leaks": 16,
      "regressions": 0
     },
     "comments": {
      "cells": 30,
      "leaks": 14,
      "regressions": 0
     },
     "raw": {
      "cells": 30,
      "leaks": 19,
      "regressions": 0
     },
     "search": {
      "cells": 30,
      "leaks": 14,
      "regressions": 0
     },
     "token_org_only": {
      "cells": 5,
      "leaks": 3,
      "regressions": 0
     },
     "token_public": {
      "cells": 5,
      "leaks": 0,
      "regressions": 0
     },
     "token_expired": {
      "cells": 5,
      "leaks": 5,
      "regressions": 0
     }
    }
   },
   "locate": {
    "say": "I read the code and found 6 places that hand back data without calling the app's own permission check, `can_access`. The check exists; it is just not used there.",
    "count": 6
   },
   "explain": {
    "say": "Here is why this app is vulnerable. IDOR (insecure direct object reference) means an app trusts an ID that the user supplies. It checks that you are logged in, but not that the item behind that ID is yours, so changing a number in the address bar shows someone else's data. It is the most common form of broken access control, the number one web risk on OWASP's list. Example: ben signs in. Their own list shows 2 item(s). They then ask for item 1 directly. The server only checks that they are signed in, so it answers with \"Q1 2026 Payroll Register\", which is not theirs. Nothing was hacked; the app simply never asked whether the item belongs to them. The table below shows each flawed endpoint, what it does wrong and a real leak I proved in the sandbox.",
    "table": "| Endpoint | What the code does | What is missing | Proven example | Leaks |\n|---|---|---|---|---|\n| GET /api/documents/{doc_id} | Looks the item up by its id with get_doc() and returns it as soon as you are logged in | A call to can_access(user, item) before the data is returned | ben (member) reached \"Q1 2026 Payroll Register\" | 14 |\n| GET /api/documents/{doc_id}/original | Looks the item up by its id with get_doc() and returns it as soon as you are logged in | A call to can_access(user, item) before the data is returned | ben (member) reached \"Q1 2026 Payroll Register\" | 16 |\n| GET /api/documents/{doc_id}/comments | Looks the item up by its id with get_doc() and returns it as soon as you are logged in | A call to can_access(user, item) before the data is returned | ben (member) reached \"Q1 2026 Payroll Register\" | 14 |\n| GET /api/search | Searches every item in the database and never filters the results to the ones you may see | A call to can_access(user, item) before the data is returned | ben (member) reached \"Q1 2026 Payroll Register\" | 14 |\n| GET /s/{token} | Opens a share link without checking that it has not expired or that it is limited to one organization | A check of the link's expiry and organization limit before returning the item | gus (admin) reached \"Q1 2026 Payroll Register\" | 8 |\n| GET /files | Serves a whole folder of files by name with no login and no ownership check | A route that calls can_access(user, item) in place of the open folder | ben (member) reached \"Q1 2026 Payroll Register\" | 19 |",
    "walkthrough": "Example: ben signs in. Their own list shows 2 item(s). They then ask for item 1 directly. The server only checks that they are signed in, so it answers with \"Q1 2026 Payroll Register\", which is not theirs. Nothing was hacked; the app simply never asked whether the item belongs to them.",
    "fix": "Call can_access(user, item) before returning data, and answer 404 when it says no."
   },
   "shots": {
    "before": [
     {
      "user": "ben",
      "doc": 1,
      "action": "read",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/documents/1",
      "file": "assets/docvault/before_0.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "original",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/documents/1/original",
      "file": "assets/docvault/before_1.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "comments",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/documents/1/comments",
      "file": "assets/docvault/before_2.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "raw",
      "verdict": "LEAK",
      "request": "HTTP 200 /files/doc_1.txt",
      "file": "assets/docvault/before_3.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "search",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/search?q=TITLE-d1-e495b0e6",
      "file": "assets/docvault/before_4.png"
     },
     {
      "user": "ben",
      "doc": 2,
      "action": "read",
      "verdict": "ALLOWED",
      "request": "HTTP 200 /api/documents/2",
      "file": "assets/docvault/before_5.png"
     }
    ],
    "after": [
     {
      "user": "ben",
      "doc": 1,
      "action": "read",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /api/documents/1",
      "file": "assets/docvault/after_0.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "original",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /api/documents/1/original",
      "file": "assets/docvault/after_1.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "comments",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /api/documents/1/comments",
      "file": "assets/docvault/after_2.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "raw",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /files/doc_1.txt",
      "file": "assets/docvault/after_3.png"
     },
     {
      "user": "ben",
      "doc": 1,
      "action": "search",
      "verdict": "BLOCKED",
      "request": "HTTP 200 /api/search?q=TITLE-d1-e495b0e6",
      "file": "assets/docvault/after_4.png"
     },
     {
      "user": "ben",
      "doc": 2,
      "action": "read",
      "verdict": "ALLOWED",
      "request": "HTTP 200 /api/documents/2",
      "file": "assets/docvault/after_5.png"
     }
    ]
   },
   "plans": [
    "GET /api/documents/{doc_id} fetches by id and never calls can_access(). Test: ben (member of Website) requests acme payroll d1. Fix: guard with can_access().",
    "GET /api/documents/{doc_id}/original must also deny viewers (cara). can_access(user, doc, 'original') already encodes that rule.",
    "GET /files serves a static folder with no authorization. Replace the mount with a guarded route that reuses can_access()."
   ],
   "patches": [
    {
     "title": "Members-only check (the obvious fix)",
     "verdict": "REJECTED",
     "say": "Rejected. It would lock out legitimate users: ana/d1/read; ana/d2/read; ana/d3/read; gus/d4/read. I will adjust the patch and try again.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": false,
      "golden_flows_identical": true,
      "legit_tests_pass": false
     },
     "closed": 14,
     "collateral": [
      "ana/d1/read ALLOW->DENY",
      "ana/d2/read ALLOW->DENY",
      "ana/d3/read ALLOW->DENY",
      "gus/d4/read ALLOW->DENY",
      "gus/d5/read ALLOW->DENY"
     ],
     "lines": 2,
     "remaining": 71,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -136,6 +136,8 @@\n @app.get(\"/api/documents/{doc_id}\")  # flaw: logged in is enough, any org, any project\n def read_document(doc_id: int, user=Depends(current_user)):\n     doc = get_doc(doc_id)\n+    if not q(\"select 1 from members where project_id=? and user=?\", doc[\"project_id\"], user[\"name\"]):\n+        raise HTTPException(404, \"no such item\")\n     return {\"id\": doc[\"id\"], \"title\": doc[\"title\"], \"content\": body(doc)}\n \n \n"
    },
    {
     "title": "Guard the read endpoint",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 14 leaks, changes 2 lines and does not affect any legitimate user. 71 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 14,
     "collateral": [],
     "lines": 2,
     "remaining": 71,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -136,6 +136,8 @@\n @app.get(\"/api/documents/{doc_id}\")  # flaw: logged in is enough, any org, any project\n def read_document(doc_id: int, user=Depends(current_user)):\n     doc = get_doc(doc_id)\n+    if not can_access(user, doc):\n+        raise HTTPException(404, \"no such item\")\n     return {\"id\": doc[\"id\"], \"title\": doc[\"title\"], \"content\": body(doc)}\n \n \n"
    },
    {
     "title": "Guard the original download",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 16 leaks, changes 2 lines and does not affect any legitimate user. 55 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 16,
     "collateral": [],
     "lines": 2,
     "remaining": 55,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -144,6 +144,8 @@\n @app.get(\"/api/documents/{doc_id}/original\")  # flaw: no tenant check and viewers can download originals\n def original(doc_id: int, user=Depends(current_user)):\n     doc = get_doc(doc_id)\n+    if not can_access(user, doc, \"original\"):\n+        raise HTTPException(404, \"no such item\")\n     return PlainTextResponse(body(doc))\n \n \n"
    },
    {
     "title": "Guard the comments endpoint",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 14 leaks, changes 2 lines and does not affect any legitimate user. 41 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 14,
     "collateral": [],
     "lines": 2,
     "remaining": 41,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -152,6 +152,8 @@\n @app.get(\"/api/documents/{doc_id}/comments\")  # flaw: comments of any document\n def comments(doc_id: int, user=Depends(current_user)):\n     doc = get_doc(doc_id)\n+    if not can_access(user, doc):\n+        raise HTTPException(404, \"no such item\")\n     return {\"comments\": q(\"select author, text from comments where doc_id=?\", doc[\"id\"])}\n \n \n"
    },
    {
     "title": "Replace the open files folder",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 19 leaks, changes 7 lines and does not affect any legitimate user. 22 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 19,
     "collateral": [],
     "lines": 7,
     "remaining": 22,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -270,4 +270,9 @@\n     return page(\"Document\", SHELL, SHELL_JS)\n \n \n-app.mount(\"/files\", StaticFiles(directory=UPLOADS), name=\"files\")  # flaw: predictable path, no auth\n+@app.get(\"/files/{fname}\")\n+def files(fname: str, user=Depends(current_user)):\n+    rows = q(\"select * from docs where fname=?\", fname)\n+    if not rows or not can_access(user, rows[0]):\n+        raise HTTPException(404, \"no such file\")\n+    return PlainTextResponse(body(rows[0]))\n"
    },
    {
     "title": "Enforce share-link rules",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 8 leaks, changes 3 lines and does not affect any legitimate user. 14 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 8,
     "collateral": [],
     "lines": 3,
     "remaining": 14,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -180,6 +180,9 @@\n     if not rows:\n         raise HTTPException(404, \"no such link\")\n     doc = get_doc(rows[0][\"doc_id\"])\n+    user = maybe_user(request)\n+    if rows[0][\"expires\"] <= NOW or (rows[0][\"org_only\"] and not (user and user[\"org\"] == doc[\"org\"])):\n+        raise HTTPException(404, \"no such link\")\n     if \"text/html\" in request.headers.get(\"accept\", \"\"):\n         return HTMLResponse(page(\"Shared document\", '<div class=\"card\"><h2>' + html.escape(doc[\"title\"]) + \"</h2><pre>\"\n                                  + html.escape(body(doc)) + \"</pre></div>\"))\n"
    },
    {
     "title": "Filter search results",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 14 leaks, changes 3 lines and does not affect any legitimate user. 0 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 14,
     "collateral": [],
     "lines": 3,
     "remaining": 0,
     "diff": "--- a/docvault/app.py\n+++ b/docvault/app.py\n@@ -159,7 +159,8 @@\n \n @app.get(\"/api/search\")  # flaw: searches every organization's titles\n def search(q_: str = Query(\"\", alias=\"q\"), user=Depends(current_user)):\n-    return brief(q(\"select * from docs where title like ?\", f\"%{q_}%\"))\n+    rows = q(\"select * from docs where title like ?\", f\"%{q_}%\")\n+    return brief([r for r in rows if can_access(user, r)])\n \n \n @app.post(\"/api/documents/{doc_id}/share\")  # correct\n"
    }
   ],
   "after": {
    "say": "I ran 165 checks and found no leaks.",
    "checks": 165,
    "proof": "I replayed 6 requests in a real browser inside the sandbox, after the fix. The same requests are now blocked while normal access still works.",
    "before_proof": "I replayed 6 requests in a real browser inside the sandbox, and 5 of them returned another account's data. Each capture shows who was signed in, the request and the response."
   },
   "court": {
    "sites": 6,
    "attacks": 18,
    "caught": 18,
    "survived": 0,
    "results": [
     {
      "line": "207",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 14 leaks the real fix closed"
     },
     {
      "line": "207",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/read, ana/d2/read, ben/d2/read"
     },
     {
      "line": "207",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/read, ana/d2/read, ben/d2/read"
     },
     {
      "line": "215",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 16 leaks the real fix closed"
     },
     {
      "line": "215",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/original, ana/d2/original, ben/d2/original"
     },
     {
      "line": "215",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/original, ana/d2/original, ben/d2/original"
     },
     {
      "line": "223",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 14 leaks the real fix closed"
     },
     {
      "line": "223",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/comments, ana/d2/comments, ben/d2/comments"
     },
     {
      "line": "223",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/comments, ana/d2/comments, ben/d2/comments"
     },
     {
      "line": "253",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 8 leaks the real fix closed"
     },
     {
      "line": "253",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: ben/d1/token_org_only, cara/d1/token_org_only, ana/d2/token_public"
     },
     {
      "line": "253",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: ben/d1/token_org_only, cara/d1/token_org_only, ana/d2/token_public"
     },
     {
      "line": "420",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 14 leaks the real fix closed"
     },
     {
      "line": "420",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/raw, ana/d2/raw, ben/d2/raw"
     },
     {
      "line": "420",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/raw, ana/d2/raw, ben/d2/raw"
     },
     {
      "line": "231",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 14 leaks the real fix closed"
     },
     {
      "line": "231",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/search, ana/d2/search, ben/d2/search"
     },
     {
      "line": "231",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: ana/d1/search, ana/d2/search, ben/d2/search"
     }
    ]
   },
   "passport": {
    "status": "VALID",
    "checks": [
     {
      "check": "content matches the signed digest",
      "ok": true,
      "detail": ""
     },
     {
      "check": "signature is valid for the embedded public key",
      "ok": true,
      "detail": "key 06d6e5d7a50130ee"
     },
     {
      "check": "fix commit exists in the repository",
      "ok": true,
      "detail": "fc7bd0513231"
     },
     {
      "check": "commit tree matches the passport",
      "ok": true,
      "detail": ""
     },
     {
      "check": "diff between base and fix matches the passport",
      "ok": true,
      "detail": ""
     },
     {
      "check": "code has not changed since the proof",
      "ok": true,
      "detail": "compared with gatewise/fix-20261010-194457"
     }
    ],
    "claim": {
     "leaks_before": 85,
     "leaks_after": 0,
     "regressions_after": 0,
     "legitimate_access_preserved": true,
     "scope": "Fixed on a sandbox copy for the tested accounts, items and doors listed here. This does not prove the absence of other flaws."
    },
    "key_id": "06d6e5d7a50130ee",
    "digest": "80a7d6ddf6b62d4b3d23953de2add35e4323619c719800511bac79669928d068",
    "code_commit": "fc7bd05132315a50018682d1c11e6c02eddd9bb1",
    "tree": "c18d4cf46cd04a677f7d01b0c4a7e607bfd88593",
    "diff_sha256": "095cdbb182a3967d7741afca8787fb6916c228fe47b8983ce562d6e201f2a95a",
    "file": "assets/docvault/passport.json",
    "page": "assets/docvault/passport.html"
   },
   "graph": {
    "path": "D:\\Gatewise\\artifacts\\docvault\\authz_graph.json",
    "edges": 165,
    "leaks_fixed": 85,
    "lessons": 1,
    "runs": 1
   },
   "pr": {
    "branch": "gatewise/fix-20261010-194457",
    "commits": 6,
    "body": "## Gatewise: fix broken access control in `docvault` (draft, needs human review)\n\nFound by differential access-control testing in a **local sandbox** (fake data only): every account was tested against every document through every endpoint,\nand each leak was proven with a canary or file hash. **85 proven leaks before, 0 after.**\n\n| patch (one flaw each) | changed lines | leaks closed |\n|---|---|---|\n| `Guard the read endpoint` | 2 | 14 |\n| `Guard the original download` | 2 | 16 |\n| `Guard the comments endpoint` | 2 | 14 |\n| `Replace the open files folder` | 7 | 19 |\n| `Enforce share-link rules` | 3 | 8 |\n| `Filter search results` | 3 | 14 |\n\n### How each patch was checked (deterministic code, not an AI)\napplies cleanly, guard-only and within the size cap, the exploit test makes progress, **only the leaking cells changed (0 collateral)**,\nnormal responses are identical, and the app's own legit-flow tests still pass.\n\n### Evidence\nBefore/after browser screenshots, logs and the verdict table: `gatewise-report/evidence.html` in this branch (self-contained: download it and open it in a browser).\n\n### Reviewer checklist\n- [ ] Each diff only adds an authorization guard that reuses the existing helper\n- [ ] The control row in the evidence report still shows legitimate access working\n- [ ] Merge manually. Gatewise never merges.\n\n_Scope: fixed on a sandbox replica for the tested user x document x door matrix; this does not prove there are no other flaws._\n",
    "table": "| Fix | Changed lines | Leaks closed |\n|---|---|---|\n| Guard the read endpoint | 2 | 14 |\n| Guard the original download | 2 | 16 |\n| Guard the comments endpoint | 2 | 14 |\n| Replace the open files folder | 7 | 19 |\n| Enforce share-link rules | 3 | 8 |\n| Filter search results | 3 | 14 |",
    "checklist": [
     "Each diff only adds an authorization guard that reuses the existing helper",
     "The control row in the report still shows legitimate access working",
     "Press Merge on the pull request yourself once you are happy"
    ],
    "leaks_before": 85,
    "leaks_after": 0,
    "report": "assets/docvault/report.html",
    "merge_link": "https://github.com/vedant91/gatewise-vulnerable-apps/pull/2",
    "say": "Here is your pull request: https://github.com/vedant91/gatewise-vulnerable-apps/pull/2. It has 6 small commits, one per flaw, and takes the app from 85 proven leaks to 0. The before and after report is committed to the branch (gatewise-report/evidence.html). It ships with a signed Access Safety Passport bound to commit fc7bd0513231, and the Patch Court caught 18 of 18 attacks on the new guards. Click the link, review the diff, and press Merge when you are happy: https://github.com/vedant91/gatewise-vulnerable-apps/pull/2. I never merge on my own."
   }
  },
  "paydesk": {
   "name": "PayDesk",
   "blurb": "A payroll portal",
   "story": "omar is an operations analyst at Acme Industries. He opens his colleague Lena Fischer's payslip, with her salary, bank details and confidential HR notes.",
   "who": "omar",
   "prompt": "Use the gatewise tools on my repository, app paydesk. Explain every step to me.",
   "pre": {
    "sandbox": "First I will build a sandbox: I copy your code, start it on localhost with fake data and check that it boots. Nothing touches production.",
    "scan": "Now I will log in as every test account and try every item through every door, to see who can reach what they should not.",
    "explain": "Let me read the code and explain, in plain words, why this app is vulnerable.",
    "proof": "I will replay the leaks in a real browser inside the sandbox, so you can see them instead of only reading about them.",
    "patch": "Now I fix it one flaw at a time. Every patch goes to the verifier, which judges it with fixed rules.",
    "after": "Let me test everything again, and replay the same browser requests after the fix.",
    "pr": "Last step: I package the fixes as a pull request with a before and after report, for you to review."
   },
   "ui": {
    "login": "assets/paydesk/ui_login.png",
    "dashboard": "assets/paydesk/ui_dashboard.png",
    "list": "assets/paydesk/ui_list.png",
    "leak": "assets/paydesk/ui_leak.png",
    "blocked": "assets/paydesk/ui_blocked.png"
   },
   "sandbox": {
    "say": "I copied paydesk from your repository into a throwaway sandbox and started it on a private localhost port with fake data. It exposes 15 endpoints (6 of them take an item id) and has 7 test accounts: priya (hr_admin), marco (manager), lena (employee), omar (employee), nora (employee), sam (hr_admin), tess (employee). Nothing here touches your real site or real data. Next I will log in as each account and test who can open what.",
    "files_copied": 4,
    "endpoints": 15,
    "endpoints_with_ids": 6,
    "accounts": 7
   },
   "scan": {
    "say": "I logged in as 7 accounts, plus an anonymous visitor, and tried every item through 8 doors (opening it, downloading it, comments, search, share links, direct file URLs). 186 of 301 checks let someone reach something they should not. A leak only counts when a hidden canary string from another account's item shows up in the response.",
    "table": "| Door | Checks | Leaks |\n|---|---|---|\n| read | 56 | 33 |\n| pdf | 56 | 37 |\n| notes | 56 | 33 |\n| raw | 56 | 40 |\n| search | 56 | 33 |\n| token_org_only | 7 | 3 |\n| token_public | 7 | 0 |\n| token_expired | 7 | 7 |",
    "leaks": 186,
    "checks": 301,
    "by_action": {
     "read": {
      "cells": 56,
      "leaks": 33,
      "regressions": 0
     },
     "pdf": {
      "cells": 56,
      "leaks": 37,
      "regressions": 0
     },
     "notes": {
      "cells": 56,
      "leaks": 33,
      "regressions": 0
     },
     "raw": {
      "cells": 56,
      "leaks": 40,
      "regressions": 0
     },
     "search": {
      "cells": 56,
      "leaks": 33,
      "regressions": 0
     },
     "token_org_only": {
      "cells": 7,
      "leaks": 3,
      "regressions": 0
     },
     "token_public": {
      "cells": 7,
      "leaks": 0,
      "regressions": 0
     },
     "token_expired": {
      "cells": 7,
      "leaks": 7,
      "regressions": 0
     }
    }
   },
   "locate": {
    "say": "I read the code and found 6 places that hand back data without calling the app's own permission check, `can_access`. The check exists; it is just not used there.",
    "count": 6
   },
   "explain": {
    "say": "Here is why this app is vulnerable. IDOR (insecure direct object reference) means an app trusts an ID that the user supplies. It checks that you are logged in, but not that the item behind that ID is yours, so changing a number in the address bar shows someone else's data. It is the most common form of broken access control, the number one web risk on OWASP's list. Example: omar signs in. Their own list shows 1 item(s). They then ask for item 1 directly. The server only checks that they are signed in, so it answers with \"Payslip January 2026, Lena Fischer\", which is not theirs. Nothing was hacked; the app simply never asked whether the item belongs to them. The table below shows each flawed endpoint, what it does wrong and a real leak I proved in the sandbox.",
    "table": "| Endpoint | What the code does | What is missing | Proven example | Leaks |\n|---|---|---|---|---|\n| GET /api/payslips/{payslip_id} | Looks the item up by its id with get_payslip() and returns it as soon as you are logged in | A call to can_access(user, item) before the data is returned | omar (employee) reached \"Payslip January 2026, Lena Fischer\" | 33 |\n| GET /api/payslips/{payslip_id}/pdf | Looks the item up by its id with get_payslip() and returns it as soon as you are logged in | A call to can_access(user, item) before the data is returned | marco (manager) reached \"Payslip January 2026, Lena Fischer\" | 37 |\n| GET /api/payslips/{payslip_id}/notes | Looks the item up by its id with get_payslip() and returns it as soon as you are logged in | A call to can_access(user, item) before the data is returned | omar (employee) reached \"Payslip January 2026, Lena Fischer\" | 33 |\n| GET /api/search | Searches every item in the database and never filters the results to the ones you may see | A call to can_access(user, item) before the data is returned | omar (employee) reached \"Payslip January 2026, Lena Fischer\" | 33 |\n| GET /s/{token} | Opens a share link without checking that it has not expired or that it is limited to one organization | A check of the link's expiry and organization limit before returning the item | sam (hr_admin) reached \"Payslip January 2026, Lena Fischer\" | 10 |\n| GET /archive | Serves a whole folder of files by name with no login and no ownership check | A route that calls can_access(user, item) in place of the open folder | omar (employee) reached \"Payslip January 2026, Lena Fischer\" | 40 |",
    "walkthrough": "Example: omar signs in. Their own list shows 1 item(s). They then ask for item 1 directly. The server only checks that they are signed in, so it answers with \"Payslip January 2026, Lena Fischer\", which is not theirs. Nothing was hacked; the app simply never asked whether the item belongs to them.",
    "fix": "Call can_access(user, item) before returning data, and answer 404 when it says no."
   },
   "shots": {
    "before": [
     {
      "user": "omar",
      "doc": 1,
      "action": "read",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/payslips/1",
      "file": "assets/paydesk/before_0.png"
     },
     {
      "user": "marco",
      "doc": 1,
      "action": "pdf",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/payslips/1/pdf",
      "file": "assets/paydesk/before_1.png"
     },
     {
      "user": "omar",
      "doc": 1,
      "action": "notes",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/payslips/1/notes",
      "file": "assets/paydesk/before_2.png"
     },
     {
      "user": "omar",
      "doc": 1,
      "action": "raw",
      "verdict": "LEAK",
      "request": "HTTP 200 /archive/payslip_1.txt",
      "file": "assets/paydesk/before_3.png"
     },
     {
      "user": "omar",
      "doc": 1,
      "action": "search",
      "verdict": "LEAK",
      "request": "HTTP 200 /api/search?q=TITLE-p1-e495b0e6",
      "file": "assets/paydesk/before_4.png"
     },
     {
      "user": "marco",
      "doc": 1,
      "action": "read",
      "verdict": "ALLOWED",
      "request": "HTTP 200 /api/payslips/1",
      "file": "assets/paydesk/before_5.png"
     }
    ],
    "after": [
     {
      "user": "omar",
      "doc": 1,
      "action": "read",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /api/payslips/1",
      "file": "assets/paydesk/after_0.png"
     },
     {
      "user": "marco",
      "doc": 1,
      "action": "pdf",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /api/payslips/1/pdf",
      "file": "assets/paydesk/after_1.png"
     },
     {
      "user": "omar",
      "doc": 1,
      "action": "notes",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /api/payslips/1/notes",
      "file": "assets/paydesk/after_2.png"
     },
     {
      "user": "omar",
      "doc": 1,
      "action": "raw",
      "verdict": "BLOCKED",
      "request": "HTTP 404 /archive/payslip_1.txt",
      "file": "assets/paydesk/after_3.png"
     },
     {
      "user": "omar",
      "doc": 1,
      "action": "search",
      "verdict": "BLOCKED",
      "request": "HTTP 200 /api/search?q=TITLE-p1-e495b0e6",
      "file": "assets/paydesk/after_4.png"
     },
     {
      "user": "marco",
      "doc": 1,
      "action": "read",
      "verdict": "ALLOWED",
      "request": "HTTP 200 /api/payslips/1",
      "file": "assets/paydesk/after_5.png"
     }
    ]
   },
   "plans": [
    "GET /api/payslips/{payslip_id} fetches by id and never calls can_access(). Test: omar (employee) requests lena's payslip. Fix: guard with can_access().",
    "GET /api/payslips/{payslip_id}/pdf must also deny managers (marco). can_access(user, ps, 'pdf') already encodes that rule.",
    "GET /archive serves a static folder with no authorization. Replace the mount with a guarded route that reuses can_access()."
   ],
   "patches": [
    {
     "title": "Members-only check (the obvious fix)",
     "verdict": "REJECTED",
     "say": "Rejected. It would lock out legitimate users: priya/d1/read; marco/d1/read; priya/d2/read; marco/d2/read. I will adjust the patch and try again.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": false,
      "golden_flows_identical": true,
      "legit_tests_pass": false
     },
     "closed": 33,
     "collateral": [
      "priya/d1/read ALLOW->DENY",
      "marco/d1/read ALLOW->DENY",
      "priya/d2/read ALLOW->DENY",
      "marco/d2/read ALLOW->DENY",
      "priya/d3/read ALLOW->DENY",
      "marco/d3/read ALLOW->DENY"
     ],
     "lines": 2,
     "remaining": 153,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -152,6 +152,8 @@\n @app.get(\"/api/payslips/{payslip_id}\")  # flaw: logged in is enough, any employee, any company\n def read_payslip(payslip_id: int, user=Depends(current_user)):\n     ps = get_payslip(payslip_id)\n+    if ps[\"employee\"] != user[\"name\"]:\n+        raise HTTPException(404, \"no such item\")\n     return {\"id\": ps[\"id\"], \"title\": ps[\"title\"], \"content\": body(ps)}\n \n \n"
    },
    {
     "title": "Guard the payslip endpoint",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 33 leaks, changes 2 lines and does not affect any legitimate user. 153 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 33,
     "collateral": [],
     "lines": 2,
     "remaining": 153,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -152,6 +152,8 @@\n @app.get(\"/api/payslips/{payslip_id}\")  # flaw: logged in is enough, any employee, any company\n def read_payslip(payslip_id: int, user=Depends(current_user)):\n     ps = get_payslip(payslip_id)\n+    if not can_access(user, ps):\n+        raise HTTPException(404, \"no such item\")\n     return {\"id\": ps[\"id\"], \"title\": ps[\"title\"], \"content\": body(ps)}\n \n \n"
    },
    {
     "title": "Guard the PDF export",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 37 leaks, changes 2 lines and does not affect any legitimate user. 116 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 37,
     "collateral": [],
     "lines": 2,
     "remaining": 116,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -160,6 +160,8 @@\n @app.get(\"/api/payslips/{payslip_id}/pdf\")  # flaw: no ownership check, and managers can export\n def payslip_pdf(payslip_id: int, user=Depends(current_user)):\n     ps = get_payslip(payslip_id)\n+    if not can_access(user, ps, \"pdf\"):\n+        raise HTTPException(404, \"no such item\")\n     return PlainTextResponse(body(ps))\n \n \n"
    },
    {
     "title": "Guard the HR notes",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 33 leaks, changes 2 lines and does not affect any legitimate user. 83 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 33,
     "collateral": [],
     "lines": 2,
     "remaining": 83,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -168,6 +168,8 @@\n @app.get(\"/api/payslips/{payslip_id}/notes\")  # flaw: HR notes of any payslip\n def payslip_notes(payslip_id: int, user=Depends(current_user)):\n     ps = get_payslip(payslip_id)\n+    if not can_access(user, ps):\n+        raise HTTPException(404, \"no such item\")\n     return {\"notes\": q(\"select author, text from notes where payslip_id=?\", ps[\"id\"])}\n \n \n"
    },
    {
     "title": "Replace the open archive folder",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 40 leaks, changes 7 lines and does not affect any legitimate user. 43 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 40,
     "collateral": [],
     "lines": 7,
     "remaining": 43,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -288,4 +288,9 @@\n     return page(\"Payslip\", SHELL, SHELL_JS)\n \n \n-app.mount(\"/archive\", StaticFiles(directory=UPLOADS), name=\"archive\")  # flaw: predictable path, no auth\n+@app.get(\"/archive/{fname}\")\n+def archive(fname: str, user=Depends(current_user)):\n+    rows = q(\"select * from payslips where fname=?\", fname)\n+    if not rows or not can_access(user, rows[0]):\n+        raise HTTPException(404, \"no such file\")\n+    return PlainTextResponse(body(rows[0]))\n"
    },
    {
     "title": "Enforce share-link rules",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 10 leaks, changes 3 lines and does not affect any legitimate user. 33 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 10,
     "collateral": [],
     "lines": 3,
     "remaining": 33,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -196,6 +196,9 @@\n     if not rows:\n         raise HTTPException(404, \"no such link\")\n     ps = get_payslip(rows[0][\"payslip_id\"])\n+    user = maybe_user(request)\n+    if rows[0][\"expires\"] <= NOW or (rows[0][\"org_only\"] and not (user and user[\"org\"] == ps[\"org\"])):\n+        raise HTTPException(404, \"no such link\")\n     if \"text/html\" in request.headers.get(\"accept\", \"\"):\n         return HTMLResponse(page(\"Shared payslip\", '<div class=\"card\"><h2>' + html.escape(ps[\"title\"]) + \"</h2><pre>\"\n                                  + html.escape(body(ps)) + \"</pre></div>\"))\n"
    },
    {
     "title": "Filter search results",
     "verdict": "ACCEPTED",
     "say": "Accepted. This patch closes 33 leaks, changes 3 lines and does not affect any legitimate user. 0 leaks are still open.",
     "gates": {
      "exploit_red_on_replica": true,
      "patch_applies": true,
      "guard_only_constraints": true,
      "exploit_progress": true,
      "blast_radius_only_leaks_flipped": true,
      "golden_flows_identical": true,
      "legit_tests_pass": true
     },
     "closed": 33,
     "collateral": [],
     "lines": 3,
     "remaining": 0,
     "diff": "--- a/paydesk/app.py\n+++ b/paydesk/app.py\n@@ -175,7 +175,8 @@\n \n @app.get(\"/api/search\")  # flaw: searches every company's payslip titles\n def search(q_: str = Query(\"\", alias=\"q\"), user=Depends(current_user)):\n-    return brief(q(\"select * from payslips where title like ?\", f\"%{q_}%\"))\n+    rows = q(\"select * from payslips where title like ?\", f\"%{q_}%\")\n+    return brief([r for r in rows if can_access(user, r)])\n \n \n @app.post(\"/api/payslips/{payslip_id}/share\")  # correct\n"
    }
   ],
   "after": {
    "say": "I ran 301 checks and found no leaks.",
    "checks": 301,
    "proof": "I replayed 6 requests in a real browser inside the sandbox, after the fix. The same requests are now blocked while normal access still works.",
    "before_proof": "I replayed 6 requests in a real browser inside the sandbox, and 5 of them returned another account's data. Each capture shows who was signed in, the request and the response."
   },
   "court": {
    "sites": 6,
    "attacks": 18,
    "caught": 18,
    "survived": 0,
    "results": [
     {
      "line": "184",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 33 leaks the real fix closed"
     },
     {
      "line": "184",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/read, marco/d1/read, lena/d1/read"
     },
     {
      "line": "184",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/read, marco/d1/read, lena/d1/read"
     },
     {
      "line": "192",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 37 leaks the real fix closed"
     },
     {
      "line": "192",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/pdf, lena/d1/pdf, priya/d2/pdf"
     },
     {
      "line": "192",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/pdf, lena/d1/pdf, priya/d2/pdf"
     },
     {
      "line": "200",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 33 leaks the real fix closed"
     },
     {
      "line": "200",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/notes, marco/d1/notes, lena/d1/notes"
     },
     {
      "line": "200",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/notes, marco/d1/notes, lena/d1/notes"
     },
     {
      "line": "230",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 10 leaks the real fix closed"
     },
     {
      "line": "230",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/token_org_only, marco/d1/token_org_only, omar/d1/token_org_only"
     },
     {
      "line": "230",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/token_org_only, marco/d1/token_org_only, omar/d1/token_org_only"
     },
     {
      "line": "401",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 33 leaks the real fix closed"
     },
     {
      "line": "401",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/raw, marco/d1/raw, lena/d1/raw"
     },
     {
      "line": "401",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/raw, marco/d1/raw, lena/d1/raw"
     },
     {
      "line": "208",
      "mutant": "guard disabled",
      "caught": true,
      "why": "reopens 33 leaks the real fix closed"
     },
     {
      "line": "208",
      "mutant": "guard inverted",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/search, marco/d1/search, lena/d1/search"
     },
     {
      "line": "208",
      "mutant": "guard blocks everyone",
      "caught": true,
      "why": "locks out legitimate users: priya/d1/search, marco/d1/search, lena/d1/search"
     }
    ]
   },
   "passport": {
    "status": "VALID",
    "checks": [
     {
      "check": "content matches the signed digest",
      "ok": true,
      "detail": ""
     },
     {
      "check": "signature is valid for the embedded public key",
      "ok": true,
      "detail": "key 06d6e5d7a50130ee"
     },
     {
      "check": "fix commit exists in the repository",
      "ok": true,
      "detail": "95f8713c3ec4"
     },
     {
      "check": "commit tree matches the passport",
      "ok": true,
      "detail": ""
     },
     {
      "check": "diff between base and fix matches the passport",
      "ok": true,
      "detail": ""
     },
     {
      "check": "code has not changed since the proof",
      "ok": true,
      "detail": "compared with gatewise/fix-20261010-194917"
     }
    ],
    "claim": {
     "leaks_before": 186,
     "leaks_after": 0,
     "regressions_after": 0,
     "legitimate_access_preserved": true,
     "scope": "Fixed on a sandbox copy for the tested accounts, items and doors listed here. This does not prove the absence of other flaws."
    },
    "key_id": "06d6e5d7a50130ee",
    "digest": "be4c019e7461c0ac21d7f1f8669c1bc1b7f8932ca90faf8f48d2949d5919a376",
    "code_commit": "95f8713c3ec412cecda934504d3e33218d8f8a7f",
    "tree": "8d80b8154bfddbc69d33ddbcaf12079ff6bdd96e",
    "diff_sha256": "4c21545f8760c2d0ed88081111ae884fc63824d2d0529c52e78ba24eaa215d87",
    "file": "assets/paydesk/passport.json",
    "page": "assets/paydesk/passport.html"
   },
   "graph": {
    "path": "D:\\Gatewise\\artifacts\\paydesk\\authz_graph.json",
    "edges": 301,
    "leaks_fixed": 186,
    "lessons": 1,
    "runs": 1
   },
   "pr": {
    "branch": "gatewise/fix-20261010-194917",
    "commits": 6,
    "body": "## Gatewise: fix broken access control in `paydesk` (draft, needs human review)\n\nFound by differential access-control testing in a **local sandbox** (fake data only): every account was tested against every document through every endpoint,\nand each leak was proven with a canary or file hash. **186 proven leaks before, 0 after.**\n\n| patch (one flaw each) | changed lines | leaks closed |\n|---|---|---|\n| `Guard the payslip endpoint` | 2 | 33 |\n| `Guard the PDF export` | 2 | 37 |\n| `Guard the HR notes` | 2 | 33 |\n| `Replace the open archive folder` | 7 | 40 |\n| `Enforce share-link rules` | 3 | 10 |\n| `Filter search results` | 3 | 33 |\n\n### How each patch was checked (deterministic code, not an AI)\napplies cleanly, guard-only and within the size cap, the exploit test makes progress, **only the leaking cells changed (0 collateral)**,\nnormal responses are identical, and the app's own legit-flow tests still pass.\n\n### Evidence\nBefore/after browser screenshots, logs and the verdict table: `gatewise-report/evidence.html` in this branch (self-contained: download it and open it in a browser).\n\n### Reviewer checklist\n- [ ] Each diff only adds an authorization guard that reuses the existing helper\n- [ ] The control row in the evidence report still shows legitimate access working\n- [ ] Merge manually. Gatewise never merges.\n\n_Scope: fixed on a sandbox replica for the tested user x document x door matrix; this does not prove there are no other flaws._\n",
    "table": "| Fix | Changed lines | Leaks closed |\n|---|---|---|\n| Guard the payslip endpoint | 2 | 33 |\n| Guard the PDF export | 2 | 37 |\n| Guard the HR notes | 2 | 33 |\n| Replace the open archive folder | 7 | 40 |\n| Enforce share-link rules | 3 | 10 |\n| Filter search results | 3 | 33 |",
    "checklist": [
     "Each diff only adds an authorization guard that reuses the existing helper",
     "The control row in the report still shows legitimate access working",
     "Press Merge on the pull request yourself once you are happy"
    ],
    "leaks_before": 186,
    "leaks_after": 0,
    "report": "assets/paydesk/report.html",
    "merge_link": null,
    "say": "Here is your pull request: branch gatewise/fix-20261010-194917 in your repository. It has 6 small commits, one per flaw, and takes the app from 186 proven leaks to 0. The before and after report is committed to the branch (gatewise-report/evidence.html). It ships with a signed Access Safety Passport bound to commit 95f8713c3ec4, and the Patch Court caught 18 of 18 attacks on the new guards. It is ready to merge once you have reviewed it. I never merge on my own. The branch is local; say the word and I will push it and open the pull request."
   }
  }
 }
};
