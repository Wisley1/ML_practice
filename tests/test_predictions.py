from unittest.mock import MagicMock

from sqlalchemy.orm import sessionmaker

from app.services.prediction_service import execute_prediction_job


def _noop_delay(*_args, **_kwargs) -> None:
    return None


def test_create_prediction_insufficient_credits(client, auth_headers, seed_ml):
    model_id = seed_ml(10)
    r = client.post(
        "/predictions",
        headers=auth_headers,
        json={"model_id": model_id, "text": "hello test"},
    )
    assert r.status_code == 402


def test_create_prediction_accepted_queued(client, auth_headers, seed_ml, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.predictions.run_prediction_task",
        MagicMock(delay=MagicMock(side_effect=_noop_delay)),
    )
    model_id = seed_ml(2)
    client.post(
        "/billing/mock-topup",
        headers=auth_headers,
        json={"credits_to_add": 50},
    )
    r = client.post(
        "/predictions",
        headers=auth_headers,
        json={"model_id": model_id, "text": "nice product"},
    )
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "queued"
    assert data["model_id"] == model_id


def test_prediction_idempotency_same_job(client, auth_headers, seed_ml, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.predictions.run_prediction_task",
        MagicMock(delay=MagicMock(side_effect=_noop_delay)),
    )
    model_id = seed_ml(1)
    client.post(
        "/billing/mock-topup",
        headers=auth_headers,
        json={"credits_to_add": 20},
    )
    body = {"model_id": model_id, "text": "same text"}
    headers = {**auth_headers, "Idempotency-Key": "idem-pytest-1"}
    r1 = client.post("/predictions", headers=headers, json=body)
    r2 = client.post("/predictions", headers=headers, json=body)
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["id"] == r2.json()["id"]


def test_prediction_completes_with_inline_worker(
    client, auth_headers, seed_ml, monkeypatch, engine
):
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(
        "app.services.prediction_service.SessionLocal",
        TestingSessionLocal,
    )

    def run_inline(job_id: int) -> None:
        execute_prediction_job(job_id)

    mock_task = MagicMock()
    mock_task.delay = MagicMock(side_effect=run_inline)
    monkeypatch.setattr(
        "app.api.routes.predictions.run_prediction_task",
        mock_task,
    )

    model_id = seed_ml(3)
    client.post(
        "/billing/mock-topup",
        headers=auth_headers,
        json={"credits_to_add": 100},
    )
    wallet_before = client.get("/wallet/me", headers=auth_headers).json()["balance_credits"]

    r = client.post(
        "/predictions",
        headers=auth_headers,
        json={"model_id": model_id, "text": "bad horrible"},
    )
    assert r.status_code == 202
    job_id = r.json()["id"]

    rj = client.get(f"/predictions/{job_id}", headers=auth_headers)
    assert rj.status_code == 200
    final = rj.json()
    assert final["status"] == "completed"
    assert final.get("result") is not None
    loy = final.get("loyalty")
    assert loy is not None
    assert loy.get("tier_name") == "bronze"

    wallet_after = client.get("/wallet/me", headers=auth_headers).json()["balance_credits"]
    assert wallet_after == wallet_before - 3

    me = client.get("/users/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["loyalty"]["tier_name"] == "bronze"
