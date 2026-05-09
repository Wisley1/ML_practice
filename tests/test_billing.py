def test_mock_topup_increases_balance(client, auth_headers):
    r = client.post(
        "/billing/mock-topup",
        headers=auth_headers,
        json={"credits_to_add": 100},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["balance_credits"] >= 100
    assert "payment_id" in body

    r2 = client.get("/wallet/me", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["balance_credits"] == body["balance_credits"]


def test_mock_topup_negative_amount_422(client, auth_headers):
    r = client.post(
        "/billing/mock-topup",
        headers=auth_headers,
        json={"credits_to_add": -10},
    )
    assert r.status_code == 422
