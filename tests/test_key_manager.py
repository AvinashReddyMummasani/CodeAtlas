"""Tests for KeyManager — Gemini API key rotation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestKeyManager:
    # ---- Module-level checks ------------------------------------------------

    def test_key_manager_module_importable(self):
        import key_manager  # noqa: F401

    def test_key_manager_has_KeyManager_or_key_status(self):
        import key_manager

        assert hasattr(key_manager, "KeyManager") or hasattr(key_manager, "key_status"), (
            "key_manager should expose KeyManager class or key_status function"
        )

    def test_key_status_is_callable(self):
        import key_manager

        assert callable(getattr(key_manager, "key_status", None)) or hasattr(
            key_manager, "KeyManager"
        )

    # ---- /api/keys/status endpoint ------------------------------------------

    def test_keys_status_endpoint_200(self, client):
        resp = client.get("/api/keys/status")
        assert resp.status_code == 200

    def test_keys_status_has_keys_field(self, client):
        resp = client.get("/api/keys/status")
        d = resp.json()
        assert "keys" in d

    def test_keys_field_is_list(self, client):
        resp = client.get("/api/keys/status")
        assert isinstance(resp.json()["keys"], list)

    def test_keys_items_have_available_field(self, client):
        resp = client.get("/api/keys/status")
        keys = resp.json().get("keys", [])
        for k in keys:
            assert "available" in k, f"Key entry missing 'available': {k}"

    def test_keys_available_is_bool(self, client):
        resp = client.get("/api/keys/status")
        keys = resp.json().get("keys", [])
        for k in keys:
            assert isinstance(k["available"], bool), (
                f"'available' should be bool, got: {type(k['available'])}"
            )

    # ---- Key rotation internals (if KeyManager is a class) ------------------

    def test_KeyManager_instantiable_no_keys(self):
        """KeyManager should be safe to instantiate even with no env keys."""
        import key_manager

        if not hasattr(key_manager, "KeyManager"):
            pytest.skip("KeyManager class not exposed")
        # Should not raise
        km = key_manager.KeyManager([])
        assert km is not None

    def test_KeyManager_instantiable_with_fake_keys(self):
        import key_manager

        if not hasattr(key_manager, "KeyManager"):
            pytest.skip("KeyManager class not exposed")
        km = key_manager.KeyManager(["fake-key-1", "fake-key-2"])
        assert km is not None
