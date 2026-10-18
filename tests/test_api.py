def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_seed_and_bootstrap(client):
    data = client.get("/api/bootstrap").json()
    assert data["onboarded"] is True
    assert data["demo_mode"] is True
    assert data["counts"]["applications"] == 7
    assert data["counts"]["messages"] == 13
    assert data["review_count"] >= 1


def test_api_requires_token(client):
    response = client.get("/api/bootstrap", headers={"X-App-Token": "wrong"})
    assert response.status_code == 401


def test_opportunities_prioritize_upcoming(client):
    items = client.get("/api/opportunities").json()
    names = [item["company"] for item in items]
    assert names.index("字节跳动") < names.index("阿里巴巴")
    assert items[0]["next_event_time"] is not None


def test_dashboard(client):
    data = client.get("/api/dashboard").json()
    assert data["stats"]["active_applications"] > 0
    assert isinstance(data["upcoming"], list)
    assert isinstance(data["action_items"], list)


def test_review_resolve(client):
    queue = client.get("/api/review").json()
    assert queue
    item = queue[0]
    response = client.post(
        f"/api/review/{item['id']}",
        json={"action": "change", "category": "技术面"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == 1.0
    assert body["decided_by"] == "human"
    assert body["category"] == "技术面"


def test_exports(client):
    csv_response = client.get("/api/export/csv")
    assert csv_response.status_code == 200
    assert "公司" in csv_response.text

    ics_response = client.get("/api/export/ics")
    assert ics_response.status_code == 200
    assert "BEGIN:VCALENDAR" in ics_response.text
    assert "BEGIN:VEVENT" in ics_response.text


def test_settings_and_secret(client):
    response = client.put(
        "/api/settings",
        json={
            "llm_provider": "deepseek",
            "llm_model": "deepseek-chat",
            "llm_api_key": "sk-test-1234",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["llm_api_key_set"] is True
    assert data["llm_api_key_preview"].endswith("1234")
    assert "sk-test" not in str(data)


def test_add_account(client):
    outlook = client.post(
        "/api/accounts",
        json={"email": "a@outlook.com", "auth_code": "x", "verify": False},
    )
    assert outlook.status_code == 400

    qq = client.post(
        "/api/accounts",
        json={"email": "new@qq.com", "auth_code": "abc", "verify": False},
    )
    assert qq.status_code == 201
    body = qq.json()
    assert body["provider"] == "qq"
    assert body["message_count"] == 0


def test_demo_account_test(client):
    response = client.post("/api/accounts/demo-account/test")
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_account_test_rejects_outlook(client):
    response = client.post(
        "/api/accounts/test",
        json={"email": "a@outlook.com", "auth_code": "x"},
    )
    assert response.status_code == 400
    assert "二期" in response.json()["detail"]


def test_sync_without_real_account(client):
    response = client.post("/api/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["message"] == "还没有添加真实邮箱"


def test_messages_endpoint(client):
    items = client.get("/api/messages").json()
    assert items
    assert "subject" in items[0]


def test_event_status_update(client):
    detail = client.get("/api/opportunities/1").json()
    event = detail["events"][-1]
    response = client.patch(f"/api/events/{event['id']}", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"
