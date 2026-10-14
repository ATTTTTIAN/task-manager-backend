def test_auth_isolation(client):
    assert client.get("/health").status_code == 200
    assert client.get("/tasks").status_code == 401

    for username in ("alice", "bob"):
        r = client.post(
            "/auth/register",
            json={
                "username": username,
                "password": "pass12345",
            },
        )
        assert r.status_code == 201, r.text

    assert client.post(
        "/auth/register",
        json={
            "username": "alice",
            "password": "pass12345",
        },
    ).status_code == 409

    tokens = {}

    for username in ("alice", "bob"):
        r = client.post(
            "/auth/login",
            data={
                "username": username,
                "password": "pass12345",
            },
        )
        assert r.status_code == 200, r.text

        tokens[username] = {
            "Authorization": "Bearer " + r.json()["access_token"]
        }

    assert client.post(
        "/auth/login",
        data={
            "username": "alice",
            "password": "wrongpass",
        },
    ).status_code == 401

    r = client.get("/auth/me", headers=tokens["alice"])
    assert r.status_code == 200
    assert r.json()["username"] == "alice"

    r = client.post(
        "/tasks",
        json={"title": "private"},
        headers=tokens["alice"],
    )
    assert r.status_code == 201, r.text

    task_id = r.json()["id"]

    assert len(
        client.get("/tasks", headers=tokens["alice"]).json()["items"]
    ) == 1

    assert client.get(
        "/tasks",
        headers=tokens["bob"],
    ).json()["items"] == []

    assert client.get(
        f"/tasks/{task_id}",
        headers=tokens["bob"],
    ).status_code == 404

    assert client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
        headers=tokens["bob"],
    ).status_code == 404

    assert client.delete(
        f"/tasks/{task_id}",
        headers=tokens["bob"],
    ).status_code == 404

    r = client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
        headers=tokens["alice"],
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    assert client.delete(
        f"/tasks/{task_id}",
        headers=tokens["alice"],
    ).status_code == 204