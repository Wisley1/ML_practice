import pytest

from app.services import auth_service


@pytest.fixture
def admin_headers(client, monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "_bootstrap_admin_emails",
        lambda: {"admintest@example.com"},
    )
    email = "admintest@example.com"
    password = "pytest12345"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_users_forbidden_for_regular_user(client, auth_headers):
    r = client.get("/admin/users", headers=auth_headers)
    assert r.status_code == 403


def test_admin_users_lists_rows(client, admin_headers):
    r = client.get("/admin/users", headers=admin_headers)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    admin_row = next(x for x in rows if x["email"] == "admintest@example.com")
    assert admin_row["role"] == "admin"
    assert "balance_credits" in admin_row
    assert "predictions_completed_last_30_days" in admin_row


def test_login_promotes_bootstrap_admin_if_was_user(client, monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "_bootstrap_admin_emails",
        lambda: set(),
    )
    email = "lateadmin@example.com"
    password = "secret12345"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    assert r.json()["role"] == "user"

    monkeypatch.setattr(
        auth_service,
        "_bootstrap_admin_emails",
        lambda: {"lateadmin@example.com"},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "admin"
