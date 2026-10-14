def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_task_lifecycle(client, auth_headers):
    r = client.post(
        "/tasks",
        json={
            "title": "学习 SQLAlchemy",
            "description": "数据库持久化",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text

    task_id = r.json()["id"]

    assert client.get(
        f"/tasks/{task_id}",
        headers=auth_headers,
    ).status_code == 200

    assert any(
        t["id"] == task_id
        for t in client.get(
            "/tasks",
            headers=auth_headers,
        ).json()["items"]
    )

    r = client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True

    r = client.get(
        "/tasks?completed=true",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1

    assert client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers,
    ).status_code == 204

    assert client.get(
        f"/tasks/{task_id}",
        headers=auth_headers,
    ).status_code == 404


def test_validation(client, auth_headers):
    assert client.post(
        "/tasks",
        json={"title": "   "},
        headers=auth_headers,
    ).status_code == 422

    assert client.post(
        "/tasks",
        json={"title": 123},
        headers=auth_headers,
    ).status_code == 422

    assert client.get(
        "/tasks?page_size=101",
        headers=auth_headers,
    ).status_code == 422

    r = client.post(
        "/tasks",
        json={"title": "OK"},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text

    task_id = r.json()["id"]

    assert client.patch(
        f"/tasks/{task_id}",
        json={"completed": None},
        headers=auth_headers,
    ).status_code == 422