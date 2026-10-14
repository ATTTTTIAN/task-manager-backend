def test_pagination(client, auth_headers):
    headers = auth_headers

    # 创建 5 条任务
    for i in range(5):
        r = client.post(
            "/tasks",
            json={"title": f"任务{i}"},
            headers=headers,
        )
        assert r.status_code == 201, r.text

    # 第一页，每页 2 条
    r = client.get(
        "/tasks?page=1&page_size=2&sort_by=id&sort_order=asc",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    assert [t["title"] for t in data["items"]] == ["任务0", "任务1"]

    # 最后一页只有 1 条
    r = client.get(
        "/tasks?page=3&page_size=2&sort_by=id&sort_order=asc",
        headers=headers,
    )
    assert r.status_code == 200
    assert [t["title"] for t in r.json()["items"]] == ["任务4"]

    # 超出总页数，返回空列表
    r = client.get(
        "/tasks?page=4&page_size=2",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 5


def test_search_and_filter(client, auth_headers):
    headers = auth_headers

    tasks = [
        ("学习 Python", False),
        ("学习 MySQL", True),
        ("Python 项目实战", True),
        ("阅读技术文档", False),
    ]

    for title, completed in tasks:
        r = client.post(
            "/tasks",
            json={"title": title},
            headers=headers,
        )
        assert r.status_code == 201, r.text

        if completed:
            task_id = r.json()["id"]
            r = client.patch(
                f"/tasks/{task_id}",
                json={"completed": True},
                headers=headers,
            )
            assert r.status_code == 200

    # 搜索 Python
    r = client.get("/tasks?keyword=Python", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2

    # 搜索 Python 且只看已完成任务
    r = client.get(
        "/tasks?keyword=Python&completed=true",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "Python 项目实战"

    # 搜索不存在的关键词
    r = client.get("/tasks?keyword=Redis", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []
    assert r.json()["total_pages"] == 0


def test_sorting(client, auth_headers):
    headers = auth_headers

    for title in ("A", "B", "C"):
        r = client.post(
            "/tasks",
            json={"title": title},
            headers=headers,
        )
        assert r.status_code == 201, r.text

    # ID 升序
    r = client.get(
        "/tasks?sort_by=id&sort_order=asc",
        headers=headers,
    )
    assert r.status_code == 200
    assert [t["title"] for t in r.json()["items"]] == ["A", "B", "C"]

    # ID 降序
    r = client.get(
        "/tasks?sort_by=id&sort_order=desc",
        headers=headers,
    )
    assert r.status_code == 200
    assert [t["title"] for t in r.json()["items"]] == ["C", "B", "A"]


def test_pagination_user_isolation(client, auth_headers):
    # auth_headers 对应 testuser
    alice_headers = auth_headers

    for i in range(3):
        r = client.post(
            "/tasks",
            json={"title": f"私人任务{i}"},
            headers=alice_headers,
        )
        assert r.status_code == 201, r.text

    # 注册另一个用户
    r = client.post(
        "/auth/register",
        json={"username": "another_user", "password": "TestPass123!"},
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/auth/login",
        data={"username": "another_user", "password": "TestPass123!"},
    )
    assert r.status_code == 200, r.text

    bob_headers = {
        "Authorization": "Bearer " + r.json()["access_token"]
    }

    # 第二个用户不应看到第一个用户的任务或总数
    r = client.get("/tasks", headers=bob_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0

    # 第一个用户仍能看到自己的 3 条任务
    r = client.get("/tasks", headers=alice_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 3