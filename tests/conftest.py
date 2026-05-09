import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.ml_models import MLModel
from app.services.loyalty_service import ensure_loyalty_tiers_seeded


def _seed_loyalty_tier(db) -> None:
    ensure_loyalty_tiers_seeded(db)
    db.commit()


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def client(engine):
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    setup = TestingSessionLocal()
    try:
        _seed_loyalty_tier(setup)
    finally:
        setup.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def db_session(engine):
    TestingSessionLocal = sessionmaker(bind=engine)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def auth_headers(client):
    email = "pytest@example.com"
    password = "pytest12345"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_ml(db_session):
    def _seed(cost_credits_base: int = 5) -> int:
        m = MLModel(
            owner_id=None,
            name="pytest-model",
            description="test",
            model_type="embeddings_sklearn",
            storage_path="",
            cost_credits_base=cost_credits_base,
            extra_metadata=None,
            is_active=True,
        )
        db_session.add(m)
        db_session.commit()
        db_session.refresh(m)
        return m.id

    return _seed
