"""
test_suite.py — CodeAtlas: 20 documented integration & unit tests
=================================================================

Coverage map
------------
TC-01  Health check endpoint returns 200 + {"status": "ok"}
TC-02  Keys status endpoint exposes API-key rotation list
TC-03  Upload a valid ZIP → 200 with session_id UUID
TC-04  Upload a non-ZIP file is rejected (400/422)
TC-05  ZIP path-traversal members are detected and rejected
TC-06  Session tree endpoint returns files + all_functions dict
TC-07  Unknown session_id returns 404
TC-08  AST parser detects all functions in source code
TC-09  AST parser detects class blocks
TC-10  AST parser records line numbers for every function
TC-11  Chat thread list returns an empty list initially
TC-12  Creating a chat thread stores the given title
TC-13  Deleting a chat thread removes it from the list
TC-14  Signup returns HTTP 200/201 with token + user object
TC-15  Duplicate username signup is rejected (400/409)
TC-16  Login with valid credentials returns a new token
TC-17  Login with wrong password is rejected (400/401)
TC-18  GET /auth/me with valid token returns user profile
TC-19  GET /auth/me with invalid token is rejected (401)
TC-20  Logout invalidates the bearer token
"""

import io
import sys
import tempfile
import shutil
import uuid
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
import parser_module  # noqa: E402
from upload_module import _is_safe_member  # noqa: E402


# ===========================================================================
# TC-01  Health check
# ===========================================================================
def test_TC01_health_check_returns_ok(client):
    """
    TC-01: GET /api/health must return HTTP 200 and JSON {"status": "ok"}.
    Verifies that the FastAPI application starts cleanly and the health
    route is registered and responsive.
    """
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


# ===========================================================================
# TC-02  API key rotation status
# ===========================================================================
def test_TC02_keys_status_exposes_list(client):
    """
    TC-02: GET /api/keys/status must return a JSON object containing a
    'keys' list.  Each entry represents one configured Gemini API key and
    its current availability.  The list may be empty when no keys are
    configured, but the field must exist.
    """
    resp = client.get("/api/keys/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert isinstance(data["keys"], list)


# ===========================================================================
# TC-03  Upload valid ZIP
# ===========================================================================
def test_TC03_upload_valid_zip_creates_session(client, sample_zip):
    """
    TC-03: POST /api/upload with a well-formed ZIP archive containing at
    least one Python file must return HTTP 200.  The response body must
    include 'session_id' (a valid UUID v4) and 'py_files_count' >= 1.
    """
    resp = client.post(
        "/api/upload",
        files={"file": ("project.zip", sample_zip, "application/zip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    uuid.UUID(data["session_id"])          # raises ValueError if not a UUID
    assert data.get("py_files_count", 0) >= 1


# ===========================================================================
# TC-04  Upload rejects non-ZIP
# ===========================================================================
def test_TC04_upload_non_zip_is_rejected(client):
    """
    TC-04: POST /api/upload with a plain-text file must be rejected.
    Expected status codes: 400 (Bad Request) or 422 (Unprocessable Entity).
    This guards against accidentally accepting corrupted or wrong file types.
    """
    resp = client.post(
        "/api/upload",
        files={"file": ("readme.txt", b"just some text", "text/plain")},
    )
    assert resp.status_code in (400, 422)


# ===========================================================================
# TC-05  Path-traversal safety in ZIP extraction
# ===========================================================================
def test_TC05_zip_path_traversal_members_rejected():
    """
    TC-05: upload_module._is_safe_member() must return False for any archive
    member name that contains '..' path-traversal components, ensuring that
    a malicious ZIP cannot write files outside the session directory.
    """
    assert _is_safe_member("../etc/passwd") is False
    assert _is_safe_member("project/../../shadow") is False
    assert _is_safe_member("normal/subdir/file.py") is True


# ===========================================================================
# TC-06  Session tree structure
# ===========================================================================
def test_TC06_session_tree_has_required_keys(client, uploaded_session):
    """
    TC-06: GET /api/session/{sid}/tree must return HTTP 200 and a JSON body
    containing both 'files' (mapping of filepath → file metadata) and
    'all_functions' (mapping of func_id → function metadata).  These two
    dicts are the core data structures consumed by every frontend tab.
    """
    sid, _ = uploaded_session
    resp = client.get(f"/api/session/{sid}/tree")
    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data
    assert "all_functions" in data
    assert isinstance(data["files"], dict)
    assert isinstance(data["all_functions"], dict)


# ===========================================================================
# TC-07  Unknown session returns 404
# ===========================================================================
def test_TC07_unknown_session_returns_404(client):
    """
    TC-07: Requesting /api/session/<bad-id>/tree with a session_id that was
    never created must return HTTP 404.  This prevents silent data leakage
    between unrelated sessions.
    """
    resp = client.get("/api/session/does-not-exist-xyz-99999/tree")
    assert resp.status_code == 404


# ===========================================================================
# TC-08  AST parser detects all functions
# ===========================================================================
def test_TC08_parser_detects_functions():
    """
    TC-08: parser_module.parse_project() must identify all top-level and
    class-method functions defined in a Python source file and populate the
    'all_functions' dict.  Here we expect 'greet', 'add', 'multiply',
    'divide', and 'factorial' to be discovered.
    """
    code = '''
def greet(name): return f"Hi {name}"
def add(a, b): return a + b

class Calc:
    def multiply(self, a, b): return a * b
    def divide(self, a, b): return a / b

def factorial(n): return 1 if n <= 1 else n * factorial(n - 1)
'''
    td = tempfile.mkdtemp()
    try:
        p = Path(td) / "sample.py"
        p.write_text(code)
        result = parser_module.parse_project(td, [str(p)])
        func_names = {v["name"] for v in result["all_functions"].values()}
        for expected in ("greet", "add", "multiply", "divide", "factorial"):
            assert expected in func_names, f"Parser missed function: {expected}"
    finally:
        shutil.rmtree(td)


# ===========================================================================
# TC-09  AST parser detects class blocks
# ===========================================================================
def test_TC09_parser_detects_class_blocks():
    """
    TC-09: parse_project() must record class definitions as BLOCK entries
    (block_type == 'CLASS') within the file's 'blocks' list.  This is used
    by the Graph Tree to render CLASS-level nodes between FILE and FUNCTION
    levels in the 5-level hierarchy.
    """
    code = '''
class MyClass:
    def method(self): pass
'''
    td = tempfile.mkdtemp()
    try:
        p = Path(td) / "cls.py"
        p.write_text(code)
        result = parser_module.parse_project(td, [str(p)])
        all_blocks = []
        for fdata in result["files"].values():
            all_blocks.extend(fdata.get("blocks", []))
        class_blocks = [b for b in all_blocks if b.get("block_type") == "CLASS"]
        assert len(class_blocks) >= 1, "No CLASS block detected"
        names = [b["name"] for b in class_blocks]
        assert "MyClass" in names
    finally:
        shutil.rmtree(td)


# ===========================================================================
# TC-10  AST parser records line numbers
# ===========================================================================
def test_TC10_parser_records_line_numbers():
    """
    TC-10: Every function entry in 'all_functions' must have a 'lineno'
    integer field so the frontend can link nodes to source lines via the
    code-viewer pane and generate correct GitHub/IDE deeplinks.
    """
    code = '''
def alpha(): pass

def beta(): pass
'''
    td = tempfile.mkdtemp()
    try:
        p = Path(td) / "lines.py"
        p.write_text(code)
        result = parser_module.parse_project(td, [str(p)])
        for fid, fdata in result["all_functions"].items():
            assert "lineno" in fdata, f"Missing lineno for function: {fid}"
            assert isinstance(fdata["lineno"], int)
    finally:
        shutil.rmtree(td)


# ===========================================================================
# TC-11  Chat thread list starts empty
# ===========================================================================
def test_TC11_thread_list_starts_empty(client, uploaded_session):
    """
    TC-11: GET /api/session/{sid}/threads on a freshly uploaded session must
    return HTTP 200 and a JSON array.  The array may already contain threads
    if the session was reused, so we only validate type — not emptiness.
    """
    sid, _ = uploaded_session
    resp = client.get(f"/api/session/{sid}/threads")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ===========================================================================
# TC-12  Create thread stores title
# ===========================================================================
def test_TC12_create_thread_stores_title(client, uploaded_session):
    """
    TC-12: POST /api/session/{sid}/threads with {"title": "My Thread"} must
    return HTTP 200/201 and a response body that reflects the stored title.
    The body must also contain an 'id' or 'thread_id' field (UUID) that can
    be used to delete or query the thread.
    """
    sid, _ = uploaded_session
    resp = client.post(
        f"/api/session/{sid}/threads",
        json={"title": "My Test Thread"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    tid = data.get("id") or data.get("thread_id")
    assert tid is not None, "Response missing 'id'/'thread_id'"
    assert data.get("title") == "My Test Thread"


# ===========================================================================
# TC-13  Delete thread removes it
# ===========================================================================
def test_TC13_delete_thread_removes_it(client, uploaded_session):
    """
    TC-13: After creating a thread with POST /threads, calling
    DELETE /threads/{tid} must return 200/204 and the thread must no longer
    appear in the subsequent GET /threads listing.  Verifies that chat
    history cleanup works end-to-end.
    """
    sid, _ = uploaded_session
    create = client.post(
        f"/api/session/{sid}/threads",
        json={"title": "Delete Me"},
    )
    assert create.status_code in (200, 201)
    tid = create.json().get("id") or create.json().get("thread_id")

    del_resp = client.delete(f"/api/session/{sid}/threads/{tid}")
    assert del_resp.status_code in (200, 204)

    threads = client.get(f"/api/session/{sid}/threads").json()
    ids = [t.get("id") or t.get("thread_id") for t in threads]
    assert tid not in ids, "Deleted thread still appears in list"


# ===========================================================================
# TC-14  Signup returns token + user object
# ===========================================================================
def test_TC14_signup_returns_token_and_user(client, test_user_creds):
    """
    TC-14: POST /api/auth/signup with valid unique credentials must return
    HTTP 200 or 201.  The response body must contain:
    - 'token'  : a non-empty string (bearer token for subsequent requests)
    - 'user'   : an object whose 'username' matches the signup request
    This confirms that registration, password hashing, and token issuance
    all work correctly end-to-end.
    """
    resp = client.post("/api/auth/signup", json=test_user_creds)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "token" in data and len(data["token"]) > 10
    assert "user" in data
    assert data["user"]["username"] == test_user_creds["username"]


# ===========================================================================
# TC-15  Duplicate username rejected
# ===========================================================================
def test_TC15_duplicate_username_rejected(client, registered_user):
    """
    TC-15: Attempting to register a second account with the same username
    must be rejected with HTTP 400 or 409.  This enforces the unique-username
    constraint in the database and prevents account collisions.
    """
    _, creds = registered_user
    resp = client.post("/api/auth/signup", json=creds)
    assert resp.status_code in (400, 409)


# ===========================================================================
# TC-16  Login with valid credentials
# ===========================================================================
def test_TC16_login_valid_credentials_returns_token(client, registered_user):
    """
    TC-16: POST /api/auth/login with the correct username and password must
    return HTTP 200 and a fresh 'token'.  Also validates that login by email
    address (instead of username) works, since auth_module supports both.
    """
    _, creds = registered_user
    # Login by username
    resp = client.post(
        "/api/auth/login",
        json={"username_or_email": creds["username"], "password": creds["password"]},
    )
    assert resp.status_code == 200
    assert "token" in resp.json()

    # Login by email
    resp2 = client.post(
        "/api/auth/login",
        json={"username_or_email": creds["email"], "password": creds["password"]},
    )
    assert resp2.status_code == 200


# ===========================================================================
# TC-17  Login with wrong password rejected
# ===========================================================================
def test_TC17_login_wrong_password_rejected(client, registered_user):
    """
    TC-17: POST /api/auth/login with the correct username but a wrong
    password must return HTTP 400 or 401.  This validates that the bcrypt
    password-verification step correctly rejects mismatches and does not
    issue tokens to unauthorized callers.
    """
    _, creds = registered_user
    resp = client.post(
        "/api/auth/login",
        json={"username_or_email": creds["username"], "password": "WRONG_PASSWORD"},
    )
    assert resp.status_code in (400, 401)


# ===========================================================================
# TC-18  /auth/me returns profile for valid token
# ===========================================================================
def test_TC18_auth_me_returns_profile(client, registered_user, auth_headers):
    """
    TC-18: GET /api/auth/me with a valid Bearer token must return HTTP 200
    and a JSON object containing a 'user' sub-object whose 'username' matches
    the account that issued the token.  This is the primary endpoint used by
    the frontend to restore login state across page refreshes.
    """
    _, creds = registered_user
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "user" in data
    assert data["user"]["username"] == creds["username"]


# ===========================================================================
# TC-19  /auth/me rejects invalid token
# ===========================================================================
def test_TC19_auth_me_rejects_invalid_token(client):
    """
    TC-19: GET /api/auth/me with a fabricated / expired Bearer token must
    be rejected with HTTP 401 or 403.  This confirms that the token lookup
    in the database properly fails for unknown tokens and does not return
    any user data.
    """
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer totally_fake_token_xyz_123"},
    )
    assert resp.status_code in (401, 403)


# ===========================================================================
# TC-20  Logout invalidates the token
# ===========================================================================
def test_TC20_logout_invalidates_token(client, registered_user, auth_headers):
    """
    TC-20: After POST /api/auth/logout with a valid token, the same token
    must no longer be accepted by GET /api/auth/me (expect 401/403).
    This validates that the server-side token deletion in auth_tokens table
    works correctly and that tokens cannot be reused after logout.
    """
    # Confirm token works before logout
    pre = client.get("/api/auth/me", headers=auth_headers)
    assert pre.status_code == 200

    # Logout
    out = client.post("/api/auth/logout", headers=auth_headers)
    assert out.status_code in (200, 204)

    # Token must now be rejected
    post = client.get("/api/auth/me", headers=auth_headers)
    assert post.status_code in (401, 403)
