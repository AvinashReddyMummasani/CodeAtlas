"""Tests for authentication endpoints (signup, login, logout, /me)."""
import uuid

import pytest


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_success_status(self, client):
        u = uuid.uuid4().hex[:8]
        resp = client.post(
            "/api/auth/signup",
            json={"username": f"user_{u}", "email": f"{u}@test.com", "password": "Secure@123"},
        )
        assert resp.status_code in (200, 201)

    def test_signup_returns_token(self, client):
        u = uuid.uuid4().hex[:8]
        resp = client.post(
            "/api/auth/signup",
            json={"username": f"tok_{u}", "email": f"{u}@x.com", "password": "P@ssw0rd"},
        )
        assert resp.status_code in (200, 201)
        assert "token" in resp.json()
        assert len(resp.json()["token"]) > 20

    def test_signup_returns_user_object(self, client):
        u = uuid.uuid4().hex[:8]
        resp = client.post(
            "/api/auth/signup",
            json={"username": f"usr_{u}", "email": f"{u}@ex.com", "password": "Secure@123"},
        )
        assert resp.status_code in (200, 201)
        assert "user" in resp.json()

    def test_signup_username_matches(self, client):
        u = uuid.uuid4().hex[:8]
        username = f"chk_{u}"
        resp = client.post(
            "/api/auth/signup",
            json={"username": username, "email": f"{u}@ex.com", "password": "Secure@123"},
        )
        assert resp.status_code in (200, 201)
        assert resp.json()["user"]["username"] == username

    def test_signup_duplicate_username_rejected(self, client, registered_user):
        _, creds = registered_user
        resp = client.post("/api/auth/signup", json=creds)
        assert resp.status_code in (400, 409)

    def test_signup_missing_email_rejected(self, client):
        resp = client.post(
            "/api/auth/signup",
            json={"username": "onlyname", "password": "pass123"},
        )
        assert resp.status_code in (400, 422)

    def test_signup_missing_password_rejected(self, client):
        u = uuid.uuid4().hex[:8]
        resp = client.post(
            "/api/auth/signup",
            json={"username": f"nopwd_{u}", "email": f"{u}@test.com"},
        )
        assert resp.status_code in (400, 422)

    def test_signup_short_password_rejected(self, client):
        u = uuid.uuid4().hex[:8]
        resp = client.post(
            "/api/auth/signup",
            json={"username": f"short_{u}", "email": f"{u}@test.com", "password": "ab"},
        )
        assert resp.status_code in (400, 422)

    def test_signup_user_has_id(self, client):
        u = uuid.uuid4().hex[:8]
        resp = client.post(
            "/api/auth/signup",
            json={"username": f"id_{u}", "email": f"{u}@test.com", "password": "Valid@123"},
        )
        assert resp.status_code in (200, 201)
        assert "id" in resp.json()["user"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_valid_credentials(self, client, registered_user):
        _, creds = registered_user
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": creds["username"], "password": creds["password"]},
        )
        assert resp.status_code == 200

    def test_login_returns_token(self, client, registered_user):
        _, creds = registered_user
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": creds["username"], "password": creds["password"]},
        )
        assert "token" in resp.json()

    def test_login_by_email(self, client, registered_user):
        _, creds = registered_user
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": creds["email"], "password": creds["password"]},
        )
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_login_wrong_password_rejected(self, client, registered_user):
        _, creds = registered_user
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": creds["username"], "password": "WRONG_PASSWORD"},
        )
        assert resp.status_code in (400, 401)

    def test_login_nonexistent_user_rejected(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": "ghost_user_xyz_999", "password": "anything"},
        )
        assert resp.status_code in (400, 401, 404)

    def test_login_missing_password_field(self, client, registered_user):
        _, creds = registered_user
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": creds["username"]},
        )
        assert resp.status_code in (400, 422)

    def test_login_token_length_reasonable(self, client, registered_user):
        _, creds = registered_user
        resp = client.post(
            "/api/auth/login",
            json={"username_or_email": creds["username"], "password": creds["password"]},
        )
        assert len(resp.json()["token"]) >= 20


# ---------------------------------------------------------------------------
# /api/auth/me
# ---------------------------------------------------------------------------

class TestMe:
    def test_me_authenticated_200(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200

    def test_me_authenticated_has_user(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert "user" in resp.json()

    def test_me_authenticated_has_projects(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert "projects" in resp.json()

    def test_me_unauthenticated_401(self, client):
        resp = client.get("/api/auth/me")
        # App returns 401 for unauthenticated /me
        assert resp.status_code in (401, 403)

    def test_me_invalid_token_rejected(self, client):
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer totally_invalid_token_xyz"},
        )
        assert resp.status_code in (401, 403)

    def test_me_username_matches_signup(self, client, registered_user, auth_headers):
        data, creds = registered_user
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.json()["user"]["username"] == creds["username"]


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_success(self, client, registered_user):
        data, creds = registered_user
        headers = {"Authorization": f"Bearer {data['token']}"}
        resp = client.post("/api/auth/logout", headers=headers)
        assert resp.status_code in (200, 204)

    def test_logout_token_invalidated(self, client, test_user_creds):
        """After logout, the same token should not grant access to /me."""
        # Fresh registration
        sign_resp = client.post("/api/auth/signup", json=test_user_creds)
        assert sign_resp.status_code in (200, 201)
        token = sign_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Confirm /me works before logout
        me_before = client.get("/api/auth/me", headers=headers)
        assert me_before.status_code == 200
        # Logout
        client.post("/api/auth/logout", headers=headers)
        # /me should now be rejected
        me_after = client.get("/api/auth/me", headers=headers)
        assert me_after.status_code in (401, 403)

    def test_logout_no_token_still_200(self, client):
        """Logout without a token should not crash the server."""
        resp = client.post("/api/auth/logout")
        assert resp.status_code in (200, 204)
