from app import cache


def test_redis_cache_hit_and_invalidation(
    client, auth_headers, monkeypatch
):
    # 使用内存字典模拟 Redis
    store = {}
    versions = {}
    hits = {"count": 0}

    def get_version(user_id):
        return versions.get(user_id, 0)

    def get_cached(key):
        value = store.get(key)
        if value is not None:
            hits["count"] += 1
        return value

    def set_cached(key, data):
        store[key] = data

    def invalidate(user_id):
        versions[user_id] = versions.get(user_id, 0) + 1

    monkeypatch.setattr(
        cache, "get_task_cache_version", get_version
    )
    monkeypatch.setattr(
        cache, "get_cached_task_page", get_cached
    )
    monkeypatch.setattr(
        cache, "set_cached_task_page", set_cached
    )
    monkeypatch.setattr(
        cache, "invalidate_task_cache", invalidate
    )

    # 第一次查询：缓存未命中
    response = client.get("/tasks", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert hits["count"] == 0
    assert len(store) == 1

    # 第二次查询：命中缓存
    response = client.get("/tasks", headers=auth_headers)
    assert response.status_code == 200
    assert hits["count"] == 1

    # 新增任务：缓存版本增加
    response = client.post(
        "/tasks",
        headers=auth_headers,
        json={"title": "Redis test"},
    )
    assert response.status_code == 201

    task_id = response.json()["id"]
    assert versions.get(1) == 1

    # 再次查询：应该读取新数据，而不是旧缓存
    response = client.get("/tasks", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Redis test"

    # 新版本缓存再次命中
    response = client.get("/tasks", headers=auth_headers)
    assert response.status_code == 200
    assert hits["count"] == 2

    # 删除任务：再次失效
    response = client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204
    assert versions.get(1) == 2

    response = client.get("/tasks", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0