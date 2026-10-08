"""Gatewise LAB portal. Deliberately vulnerable (L1-L5 + hidden V1/V2). Fake data only. Never deploy."""
import hashlib, html, os, sqlite3, time
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("PORTAL_DB", os.path.join(HERE, "portal.db"))
UPLOADS = os.environ.get("PORTAL_UPLOADS", os.path.join(HERE, "uploads"))
SEED = os.environ.get("SEED", "42")
NOW = int(os.environ.get("PORTAL_NOW", "1767225600"))  # fixed clock: 2026-01-01
SECRET = "lab-secret"

USERS = [("alice", "user", "A"), ("bob", "user", None), ("dave", "user", "A"), ("admin", "admin", None)]
DOCS = [  # id, title, owner, team, public
    (1, "Alice salary slip", "alice", None, 0),
    (2, "Alice employment contract", "alice", None, 0),
    (3, "Bob offer letter", "bob", None, 0),
    (4, "Team-A handbook", "alice", "A", 0),
    (5, "Company brochure", "admin", None, 1),
    (6, "Admin policy", "admin", None, 0),
]


def tag(doc_id):
    return hashlib.sha1(f"{SEED}:{doc_id}".encode()).hexdigest()[:8]


def q(sql, *a):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in c.execute(sql, a)]
        c.commit()
        return rows
    finally:
        c.close()


def init_db():
    os.makedirs(UPLOADS, exist_ok=True)
    if os.path.exists(DB):
        return
    q("create table users(name text, pw text, role text, team text)")
    q("create table docs(id int, title text, owner text, team text, public int, fname text)")
    q("create table shares(doc_id int, user text)")
    q("create table tokens(token text primary key, doc_id int, recipient text, expires int)")
    for n, role, team in USERS:
        q("insert into users values(?,?,?,?)", n, "pw-" + n, role, team)
    for i, title, owner, team, public in DOCS:
        fname = f"doc_{i}.txt"
        q("insert into docs values(?,?,?,?,?,?)", i, f"{title} TITLE-d{i}-{tag(i)}", owner, team, public, fname)
        with open(os.path.join(UPLOADS, fname), "w", newline="") as f:  # LF on every OS, so file bytes == response bytes
            f.write(f"{title}\nsecret: CANARY-d{i}-{tag(i)}\n")
    q("insert into shares values(2,'bob')")


init_db()
app = FastAPI()


def sign(name):
    return name + "." + hashlib.sha256((name + SECRET).encode()).hexdigest()[:16]


def maybe_user(request: Request):
    sid = request.cookies.get("sid", "")
    name, _, sig = sid.partition(".")
    if sid and sign(name) == sid:
        rows = q("select * from users where name=?", name)
        return rows[0] if rows else None
    return None


def current_user(request: Request):
    user = maybe_user(request)
    if not user:
        raise HTTPException(401, "login required")
    return user


def get_document(doc_id: int):
    rows = q("select * from docs where id=?", doc_id)
    if not rows:
        raise HTTPException(404, "no such document")
    return rows[0]


def body(doc):
    with open(os.path.join(UPLOADS, doc["fname"])) as f:
        return f.read()


def can_access(user, doc, action="read"):
    """The CORRECT authorization rule. Only /share uses it (that is the seeded bug)."""
    if user["role"] == "admin" or doc["owner"] == user["name"]:
        return True
    if action == "share":
        return False
    if doc["public"]:
        return True
    if doc["team"] and doc["team"] == user["team"]:
        return True
    return bool(q("select 1 from shares where doc_id=? and user=?", doc["id"], user["name"]))


def brief(rows):
    return {"documents": [{"id": r["id"], "title": r["title"]} for r in rows]}


@app.post("/login")
async def login(request: Request, response: Response):
    data = await request.json()
    rows = q("select * from users where name=? and pw=?", data.get("name"), data.get("password"))
    if not rows:
        raise HTTPException(401, "bad credentials")
    response.set_cookie("sid", sign(rows[0]["name"]))
    return {"ok": True}


@app.get("/documents")  # "My Documents"
def my_documents(user=Depends(current_user)):
    return brief(q("select * from docs where owner=?", user["name"]))


@app.get("/shared")
def shared(user=Depends(current_user)):
    return brief(q("select d.* from docs d join shares s on s.doc_id=d.id where s.user=?", user["name"]))


@app.get("/team")
def team(user=Depends(current_user)):
    return brief(q("select * from docs where team=?", user["team"])) if user["team"] else brief([])


@app.get("/public")
def public(user=Depends(current_user)):
    return brief(q("select * from docs where public=1"))


@app.get("/admin/documents")
def admin_documents(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "admin only")
    return brief(q("select * from docs"))


@app.get("/documents/{doc_id}")  # L1: authenticated, never authorized
def read_document(doc_id: int, user=Depends(current_user)):
    doc = get_document(doc_id)
    return {"id": doc["id"], "title": doc["title"], "content": body(doc)}


@app.get("/documents/{doc_id}/preview")  # L2
def preview(doc_id: int, user=Depends(current_user)):
    doc = get_document(doc_id)
    return HTMLResponse(f"<html><body><h1>{html.escape(doc['title'])}</h1><pre>{html.escape(body(doc))}</pre></body></html>")


@app.get("/download")  # L2
def download(id: int, user=Depends(current_user)):
    doc = get_document(id)
    return PlainTextResponse(body(doc))


@app.get("/documents/{doc_id}/versions")  # hidden V1
def versions(doc_id: int, user=Depends(current_user)):
    doc = get_document(doc_id)
    return {"versions": [{"v": 1, "content": body(doc)}]}


@app.get("/documents/{doc_id}/export")  # hidden V2
def export(doc_id: int, user=Depends(current_user)):
    doc = get_document(doc_id)
    return PlainTextResponse(body(doc))


@app.post("/documents/{doc_id}/share")  # the one endpoint that DOES authorize
async def share(doc_id: int, request: Request, user=Depends(current_user)):
    doc = get_document(doc_id)
    if not can_access(user, doc, "share"):
        raise HTTPException(403, "only the owner may share")
    data = await request.json()
    recipient, ttl = data.get("recipient"), int(data.get("ttl", 3600))
    token = "tok-" + hashlib.sha1(f"{SEED}:{doc_id}:{recipient}:{ttl}".encode()).hexdigest()[:12]
    q("insert or replace into tokens values(?,?,?,?)", token, doc_id, recipient, NOW + ttl)
    return {"token": token}


@app.get("/s/{token}")  # L4: no recipient check, no expiry check
def open_share(token: str, request: Request):
    rows = q("select * from tokens where token=?", token)
    if not rows:
        raise HTTPException(404, "no such link")
    doc = get_document(rows[0]["doc_id"])
    return {"id": doc["id"], "title": doc["title"], "content": body(doc)}


@app.get("/search")  # L5: matches every user's titles
def search(q_: str = Query("", alias="q"), user=Depends(current_user)):
    return brief(q("select * from docs where title like ?", f"%{q_}%"))


app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")  # L3: predictable path, no auth
