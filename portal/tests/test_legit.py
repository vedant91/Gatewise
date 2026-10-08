"""Legit-flow tests. Must pass on the vulnerable build AND after any accepted patch.
PORTAL_DIR (default: the folder above tests/) says which copy of the portal to test."""
import os, sys
import pytest
from fastapi.testclient import TestClient

PORTAL = os.environ.get("PORTAL_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def mod(tmp_path_factory):
    d = tmp_path_factory.mktemp("lab")
    os.environ["PORTAL_DB"] = str(d / "p.db")
    os.environ["PORTAL_UPLOADS"] = str(d / "up")
    sys.path.insert(0, PORTAL)
    sys.modules.pop("app", None)
    import app
    yield app
    sys.path.remove(PORTAL)
    sys.modules.pop("app", None)


def who(mod, name=None):
    c = TestClient(mod.app)
    if name:
        assert c.post("/login", json={"name": name, "password": "pw-" + name}).status_code == 200
    return c


def ids(r):
    assert r.status_code == 200
    return {d["id"] for d in r.json()["documents"]}


@pytest.mark.parametrize("user,doc", [
    ("alice", 1), ("alice", 2), ("alice", 4),   # owner
    ("bob", 3), ("bob", 2),                     # owner; shared-with
    ("dave", 4),                                # team
    ("bob", 5), ("alice", 5), ("dave", 5),      # public brochure
    ("admin", 1), ("admin", 2), ("admin", 3), ("admin", 4), ("admin", 5), ("admin", 6),  # admin sees all
])
@pytest.mark.parametrize("path", ["/documents/{d}", "/documents/{d}/preview", "/download?id={d}",
                                  "/documents/{d}/versions", "/documents/{d}/export"])
def test_legit_read(mod, user, doc, path):
    r = who(mod, user).get(path.format(d=doc))
    assert r.status_code == 200 and f"CANARY-d{doc}-" in r.text


@pytest.mark.parametrize("user,doc", [("alice", 1), ("bob", 2), ("dave", 4), ("admin", 6), ("bob", 5)])
def test_legit_raw_file(mod, user, doc):
    r = who(mod, user).get(f"/uploads/doc_{doc}.txt")
    assert r.status_code == 200 and f"CANARY-d{doc}-" in r.text


def test_list_views(mod):
    assert ids(who(mod, "alice").get("/documents")) == {1, 2, 4}
    assert ids(who(mod, "bob").get("/shared")) == {2}
    assert ids(who(mod, "dave").get("/team")) == {4}
    assert ids(who(mod, "bob").get("/public")) == {5}
    assert ids(who(mod, "admin").get("/admin/documents")) == {1, 2, 3, 4, 5, 6}
    assert who(mod, "bob").get("/admin/documents").status_code == 403


def test_search_finds_own_and_shared(mod):
    assert "TITLE-d1-" in who(mod, "alice").get("/search", params={"q": "TITLE-d1"}).text
    assert "TITLE-d2-" in who(mod, "bob").get("/search", params={"q": "TITLE-d2"}).text


def test_recipient_token_works_for_recipient(mod):
    tok = who(mod, "alice").post("/documents/2/share", json={"recipient": "bob", "ttl": 3600}).json()["token"]
    r = who(mod, "bob").get(f"/s/{tok}")
    assert r.status_code == 200 and "CANARY-d2-" in r.text


def test_public_token_works_for_anonymous(mod):
    tok = who(mod, "admin").post("/documents/5/share", json={"ttl": 3600}).json()["token"]
    r = who(mod).get(f"/s/{tok}")
    assert r.status_code == 200 and "CANARY-d5-" in r.text


def test_only_owner_may_share(mod):
    assert who(mod, "bob").post("/documents/1/share", json={}).status_code == 403
    assert who(mod, "alice").post("/documents/1/share", json={"ttl": 5}).status_code == 200


def test_login_required(mod):
    assert who(mod).get("/documents").status_code == 401
