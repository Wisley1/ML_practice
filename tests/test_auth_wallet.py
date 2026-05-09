def test_register_login_wallet(client):
    email = "u1@example.com"
    password = "secret12345"

    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    assert r.json()["email"] == email

    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/wallet/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["balance_credits"] == 0
    assert "user_id" in body


def test_register_duplicate_returns_409(client):
    email = "dup@example.com"
    password = "secret12345"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 409


def test_register_short_password_422(client):
    r = client.post(
        "/auth/register",
        json={"email": "shortpw@example.com", "password": "12345"},
    )
    assert r.status_code == 422
    detail = r.json().get("detail", [])
    assert isinstance(detail, list)
    assert any("password" in str(item).lower() for item in detail) or len(detail) >= 1


def test_register_invalid_email_422(client):
    r = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "secret12345"},
    )
    assert r.status_code == 422
