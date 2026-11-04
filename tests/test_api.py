import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def make_bug(client, **overrides):
    payload = {
        "title": "Login button does nothing",
        "description": "Clicking login on Safari has no effect.",
        "severity": "High",
        "status": "Open",
    }
    payload.update(overrides)
    return client.post("/api/bugs", json=payload)


def test_create_bug_returns_201_and_saved_fields(client):
    res = make_bug(client)
    assert res.status_code == 201
    body = res.get_json()
    assert body["id"] == 1
    assert body["title"] == "Login button does nothing"
    assert body["severity"] == "High"
    assert body["status"] == "Open"


def test_create_uses_defaults_when_optional_fields_missing(client):
    res = client.post("/api/bugs", json={"title": "Typo on home page"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["severity"] == "Medium"
    assert body["status"] == "Open"
    assert body["description"] == ""


def test_create_rejects_missing_title(client):
    res = client.post("/api/bugs", json={"severity": "Low"})
    assert res.status_code == 400
    assert "Title" in res.get_json()["error"]


def test_create_rejects_blank_title(client):
    res = make_bug(client, title="   ")
    assert res.status_code == 400


def test_create_rejects_invalid_severity(client):
    res = make_bug(client, severity="Urgent")
    assert res.status_code == 400
    assert "Severity" in res.get_json()["error"]


def test_create_rejects_non_json_body(client):
    res = client.post("/api/bugs", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_list_returns_newest_first(client):
    make_bug(client, title="First")
    make_bug(client, title="Second")
    titles = [b["title"] for b in client.get("/api/bugs").get_json()]
    assert titles == ["Second", "First"]


def test_filter_by_severity_and_status(client):
    make_bug(client, title="A", severity="High", status="Open")
    make_bug(client, title="B", severity="High", status="Fixed")
    make_bug(client, title="C", severity="Low", status="Open")
    res = client.get("/api/bugs?severity=High&status=Open")
    assert [b["title"] for b in res.get_json()] == ["A"]


def test_search_matches_title_and_description(client):
    make_bug(client, title="Crash on upload", description="Large PNG files")
    make_bug(client, title="Slow page", description="Dashboard takes 8 seconds")
    assert len(client.get("/api/bugs?q=crash").get_json()) == 1
    assert len(client.get("/api/bugs?q=dashboard").get_json()) == 1
    assert client.get("/api/bugs?q=nothing-here").get_json() == []


def test_get_single_bug_and_404_for_missing(client):
    make_bug(client)
    assert client.get("/api/bugs/1").status_code == 200
    assert client.get("/api/bugs/99").status_code == 404


def test_update_status_only(client):
    make_bug(client)
    res = client.put("/api/bugs/1", json={"status": "In Progress"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "In Progress"
    assert body["title"] == "Login button does nothing"  # untouched


def test_update_rejects_invalid_status(client):
    make_bug(client)
    res = client.put("/api/bugs/1", json={"status": "Done"})
    assert res.status_code == 400


def test_update_missing_bug_returns_404(client):
    res = client.put("/api/bugs/42", json={"status": "Fixed"})
    assert res.status_code == 404


def test_delete_bug(client):
    make_bug(client)
    assert client.delete("/api/bugs/1").status_code == 204
    assert client.get("/api/bugs/1").status_code == 404
    assert client.delete("/api/bugs/1").status_code == 404


def test_stats_counts_by_status_and_severity(client):
    make_bug(client, severity="High", status="Open")
    make_bug(client, severity="High", status="Fixed")
    make_bug(client, severity="Low", status="Fixed")
    stats = client.get("/api/stats").get_json()
    assert stats["total"] == 3
    assert stats["status"] == {"Open": 1, "In Progress": 0, "Fixed": 2}
    assert stats["severity"] == {"Low": 1, "Medium": 0, "High": 2}
