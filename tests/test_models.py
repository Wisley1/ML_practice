def test_list_models_returns_list(client):
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_list_models_entries_shape(client, seed_ml):
    seed_ml(1)
    r = client.get("/models")
    assert r.status_code == 200
    models = r.json()
    assert len(models) >= 1
    for m in models:
        assert isinstance(m, dict)
        assert "id" in m
        assert "name" in m
