import pytest


@pytest.mark.asyncio
async def test_create_learner_returns_201(authed_client):
    client, parent = authed_client
    response = await client.post(
        "/learners",
        json={"name": "Emma", "age": 6, "grade_level": 1, "avatar_emoji": "🦋"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Emma"
    assert body["age"] == 6
    assert body["grade_level"] == 1
    assert body["total_stars"] == 0
    assert body["level"] == 1
    assert "id" in body


@pytest.mark.asyncio
async def test_create_learner_rejects_age_out_of_range(authed_client):
    client, _ = authed_client
    response = await client.post("/learners", json={"name": "Emma", "age": 10, "grade_level": 1})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_learner_rejects_grade_out_of_range(authed_client):
    client, _ = authed_client
    response = await client.post("/learners", json={"name": "Emma", "age": 6, "grade_level": 5})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_learners(authed_client):
    client, _ = authed_client
    await client.post("/learners", json={"name": "A", "age": 5, "grade_level": 0})
    await client.post("/learners", json={"name": "B", "age": 8, "grade_level": 3})
    response = await client.get("/learners")
    assert response.status_code == 200
    assert len(response.json()["learners"]) >= 2


@pytest.mark.asyncio
async def test_get_learner_by_id(authed_client):
    client, _ = authed_client
    create_resp = await client.post("/learners", json={"name": "C", "age": 7, "grade_level": 2})
    learner_id = create_resp.json()["id"]
    response = await client.get(f"/learners/{learner_id}")
    assert response.status_code == 200
    assert response.json()["id"] == learner_id


@pytest.mark.asyncio
async def test_get_learner_returns_404_for_nonexistent(authed_client):
    from uuid_extensions import uuid7

    client, _ = authed_client
    response = await client.get(f"/learners/{uuid7()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_learner(authed_client):
    client, _ = authed_client
    create_resp = await client.post("/learners", json={"name": "D", "age": 6, "grade_level": 1})
    learner_id = create_resp.json()["id"]
    response = await client.patch(f"/learners/{learner_id}", json={"name": "D Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "D Updated"
