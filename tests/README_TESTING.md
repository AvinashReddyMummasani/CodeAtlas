# CodeAtlas — Test Suite Documentation

## Overview

The test suite covers all critical layers of the CodeAtlas backend through
**20 documented integration and unit tests** (`tests/test_suite.py`).  
Tests are run against the real FastAPI application via Starlette's
`TestClient` — no live server or network is needed.

---

## Running the Tests

```bash
# From the project root (c:\sem5\SE\LAB PROJECT)
python -m pytest tests/test_suite.py -v
```

Or simply:
```bash
pytest
```

---

## Test Case Reference

| ID | Test Name | Layer | Description |
|----|-----------|-------|-------------|
| TC-01 | `test_TC01_health_check_returns_ok` | API | `GET /api/health` → 200 + `{"status":"ok"}` |
| TC-02 | `test_TC02_keys_status_exposes_list` | API | Key-rotation endpoint exposes a `keys` list |
| TC-03 | `test_TC03_upload_valid_zip_creates_session` | Upload | Valid ZIP → 200 + UUID session_id + file count |
| TC-04 | `test_TC04_upload_non_zip_is_rejected` | Upload | Plain-text file upload → 400 / 422 |
| TC-05 | `test_TC05_zip_path_traversal_members_rejected` | Security | `..` path-traversal in ZIP member names rejected |
| TC-06 | `test_TC06_session_tree_has_required_keys` | Session | Tree response has `files` + `all_functions` dicts |
| TC-07 | `test_TC07_unknown_session_returns_404` | Session | Unknown `session_id` → 404 |
| TC-08 | `test_TC08_parser_detects_functions` | Parser | AST detects all top-level + method functions |
| TC-09 | `test_TC09_parser_detects_class_blocks` | Parser | AST detects CLASS-level BLOCK nodes |
| TC-10 | `test_TC10_parser_records_line_numbers` | Parser | Every function entry has an integer `lineno` |
| TC-11 | `test_TC11_thread_list_starts_empty` | Threads | `GET /threads` returns JSON list |
| TC-12 | `test_TC12_create_thread_stores_title` | Threads | POST creates thread with correct title + id |
| TC-13 | `test_TC13_delete_thread_removes_it` | Threads | DELETE removes thread from subsequent GET list |
| TC-14 | `test_TC14_signup_returns_token_and_user` | Auth | Signup → 200/201 + token + matching user object |
| TC-15 | `test_TC15_duplicate_username_rejected` | Auth | Second signup with same username → 400/409 |
| TC-16 | `test_TC16_login_valid_credentials_returns_token` | Auth | Login by username & email both return token |
| TC-17 | `test_TC17_login_wrong_password_rejected` | Auth | Wrong password → 400/401 |
| TC-18 | `test_TC18_auth_me_returns_profile` | Auth | Valid token → `/auth/me` returns user profile |
| TC-19 | `test_TC19_auth_me_rejects_invalid_token` | Auth | Fake token → 401/403 |
| TC-20 | `test_TC20_logout_invalidates_token` | Auth | Post-logout token is rejected by `/auth/me` |

---

## Fixtures (`conftest.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `client` | session | Shared `TestClient` — app starts once per run |
| `sample_zip` | session | In-memory ZIP with 2 Python files |
| `uploaded_session` | session | Uploads `sample_zip`, returns `(session_id, data)` |
| `test_user_creds` | function | Fresh unique credentials per test |
| `registered_user` | function | Signs up a user, returns `(data, creds)` |
| `auth_headers` | function | `Authorization: Bearer <token>` dict |

---

## Notes

- **TC-08 to TC-10** test `parser_module` directly (pure Python, no HTTP)  
- **TC-05** tests `upload_module._is_safe_member()` directly (security unit test)  
- Some tests (TC-06, TC-11–13) depend on `uploaded_session` and will be skipped if the upload fails  
- Auth tests (TC-14–20) create unique users via `uuid4()` — safe to run repeatedly  
- Run time: ~3–5 minutes (Gemini API calls during the upload fixture)

---

## Adding More Tests

Add new `test_TC21_...` functions to `tests/test_suite.py` following the
docstring format used by existing tests (purpose, expected behavior, rationale).
