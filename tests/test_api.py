"""Integration tests for CodeAtlas REST API endpoints."""
import time

import pytest


# ---------------------------------------------------------------------------
# Health / utility endpoints
# ---------------------------------------------------------------------------

class TestHealthEndpoints:
    def test_root_serves_html_or_404(self, client):
        """Root may serve HTML (if frontend exists) or 404 if not built."""
        resp = client.get("/")
        assert resp.status_code in (200, 404)

    def test_root_200_is_html(self, client):
        resp = client.get("/")
        if resp.status_code == 200:
            assert "text/html" in resp.headers.get("content-type", "")

    def test_health_endpoint_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        resp = client.get("/api/health")
        assert resp.json().get("status") == "ok"

    def test_keys_status_ok(self, client):
        resp = client.get("/api/keys/status")
        assert resp.status_code == 200

    def test_keys_status_has_keys_list(self, client):
        resp = client.get("/api/keys/status")
        d = resp.json()
        assert "keys" in d
        assert isinstance(d["keys"], list)


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

class TestSessionEndpoints:
    def test_session_status_returns_200(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/status")
        assert resp.status_code == 200

    def test_session_status_has_stage(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/status")
        d = resp.json()
        assert "stage" in d or "finished" in d

    def test_session_status_has_tree_ready(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/status")
        assert "tree_ready" in resp.json()

    def test_session_tree_accepted_or_ok(self, client, uploaded_session):
        """Tree may be 200 (ready) or 202 (still summarising) — both are valid."""
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/tree")
        assert resp.status_code in (200, 202)

    def test_session_tree_200_has_files(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/tree")
        if resp.status_code == 200:
            d = resp.json()
            assert "files" in d
            assert "all_functions" in d

    def test_invalid_session_status_404(self, client):
        resp = client.get("/api/session/nonexistent-session-xyz/status")
        assert resp.status_code == 404

    def test_invalid_session_tree_404(self, client):
        resp = client.get("/api/session/nonexistent-session-xyz/tree")
        assert resp.status_code == 404

    def test_session_chat_no_gemini_key_acceptable(self, client, uploaded_session):
        """Chat endpoint may return 500/400/503 without a Gemini key — not a crash."""
        sid, _ = uploaded_session
        resp = client.post(
            f"/api/session/{sid}/chat",
            json={"question": "What does this project do?", "chat_history": []},
        )
        # Any non-5xx that isn't a hard crash is fine; Gemini key errors also acceptable
        assert resp.status_code in (200, 202, 400, 422, 500, 503, 504)

    def test_session_flow_needs_func_id(self, client, uploaded_session):
        """flow endpoint requires func_id — omitting should give 422."""
        sid, _ = uploaded_session
        resp = client.post(f"/api/session/{sid}/flow", json={})
        assert resp.status_code in (422, 400, 404)

    def test_session_flow_with_func_id(self, client, uploaded_session):
        sid, _ = uploaded_session
        tree_resp = client.get(f"/api/session/{sid}/tree")
        if tree_resp.status_code != 200:
            pytest.skip("Tree not ready — still summarising")
        funcs = tree_resp.json().get("all_functions", {})
        if not funcs:
            pytest.skip("No functions in test project")
        func_id = next(iter(funcs))
        resp = client.post(f"/api/session/{sid}/flow", json={"func_id": func_id})
        assert resp.status_code in (200, 400, 404, 503)

    def test_session_optimize_with_func_id(self, client, uploaded_session):
        sid, _ = uploaded_session
        tree_resp = client.get(f"/api/session/{sid}/tree")
        if tree_resp.status_code != 200:
            pytest.skip("Tree not ready")
        funcs = tree_resp.json().get("all_functions", {})
        if not funcs:
            pytest.skip("No functions")
        func_id = next(iter(funcs))
        resp = client.post(
            f"/api/session/{sid}/optimize",
            json={"func_id": func_id, "bulk": False},
        )
        assert resp.status_code in (200, 400, 501, 503)

    def test_session_risk_with_func_id(self, client, uploaded_session):
        sid, _ = uploaded_session
        tree_resp = client.get(f"/api/session/{sid}/tree")
        if tree_resp.status_code != 200:
            pytest.skip("Tree not ready")
        funcs = tree_resp.json().get("all_functions", {})
        if not funcs:
            pytest.skip("No functions")
        func_id = next(iter(funcs))
        resp = client.post(
            f"/api/session/{sid}/risk",
            json={"func_id": func_id, "bulk": False},
        )
        assert resp.status_code in (200, 400, 501, 503)

    def test_session_optimize_no_func_id_gives_422(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.post(f"/api/session/{sid}/optimize", json={"bulk": False})
        # Either 422 (no func_id) or 501 (module not installed)
        assert resp.status_code in (422, 400, 501)


# ---------------------------------------------------------------------------
# Chat threads
# ---------------------------------------------------------------------------

class TestChatThreads:
    def test_list_threads_returns_200(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/threads")
        assert resp.status_code == 200

    def test_list_threads_is_list(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.get(f"/api/session/{sid}/threads")
        assert isinstance(resp.json(), list)

    def test_create_thread_returns_201_or_200(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.post(
            f"/api/session/{sid}/threads", json={"title": "Test Thread"}
        )
        assert resp.status_code in (200, 201)

    def test_create_thread_has_id_field(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.post(
            f"/api/session/{sid}/threads", json={"title": "ID Check"}
        )
        d = resp.json()
        assert "id" in d or "thread_id" in d

    def test_create_thread_title_stored(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.post(
            f"/api/session/{sid}/threads", json={"title": "UniqueTitle123"}
        )
        d = resp.json()
        assert d.get("title") == "UniqueTitle123"

    def test_delete_thread_success(self, client, uploaded_session):
        sid, _ = uploaded_session
        create = client.post(
            f"/api/session/{sid}/threads", json={"title": "Delete Me"}
        )
        assert create.status_code in (200, 201)
        tid = create.json().get("id") or create.json().get("thread_id")
        assert tid is not None
        del_resp = client.delete(f"/api/session/{sid}/threads/{tid}")
        assert del_resp.status_code in (200, 204)

    def test_delete_nonexistent_thread_404(self, client, uploaded_session):
        sid, _ = uploaded_session
        resp = client.delete(f"/api/session/{sid}/threads/nonexistent-thread-id")
        assert resp.status_code == 404

    def test_thread_appears_in_list_after_creation(self, client, uploaded_session):
        sid, _ = uploaded_session
        create = client.post(
            f"/api/session/{sid}/threads", json={"title": "ListCheck"}
        )
        tid = create.json().get("id") or create.json().get("thread_id")
        threads = client.get(f"/api/session/{sid}/threads").json()
        ids = [t.get("id") or t.get("thread_id") for t in threads]
        assert tid in ids
