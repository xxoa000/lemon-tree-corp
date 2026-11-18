from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health():
    assert client.get('/health').json() == {'status': 'ok'}

def test_org_has_eleven_members():
    assert len(client.get('/api/v1/employees').json()) == 11

def test_three_teams_and_all_members():
    teams = client.get('/api/v1/teams').json()
    assert len(teams) == 3
    assert sum(len(team['member_ids']) for team in teams) == 10  # CEO is outside the three teams

def test_manager_is_external_and_has_rank():
    manager = client.get('/api/v1/control-center/manager').json()
    assert manager['rank'] == '부장'
    assert manager['external_to_org'] is True
    assert manager['invocation_semantics'] == 'OWNER_DESIGN_REQUEST'


def test_task_status_requires_ownership_and_survives_new_request(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "workplace.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "test-signing-key-for-workplace-tests")
    monkeypatch.setenv("WORKPLACE_PASSWORD", "local-test-password")
    monkeypatch.setenv("WORKPLACE_USERNAME", "junior")
    monkeypatch.delenv("WORKPLACE_SECURE_COOKIE", raising=False)
    update = {"status": "done"}

    with TestClient(app) as reviewer:
        assert reviewer.patch("/api/v1/tasks/LT-21", json=update).status_code == 401
        assert reviewer.post("/api/v1/session", json={
            "username": "junior", "password": "wrong",
        }).status_code == 401
        login_response = reviewer.post("/api/v1/session", json={
            "username": "junior", "password": "local-test-password",
        })
        assert login_response.json() == {"employee_id": "LT-011", "org_employee_id": "LT-011", "role": "member"}
        assert "httponly" in login_response.headers["set-cookie"].lower()
        assert reviewer.patch("/api/v1/tasks/LT-22", json=update).status_code == 403
        assert reviewer.patch("/api/v1/tasks/LT-21", json=update).json()["status"] == "done"
        assert reviewer.delete("/api/v1/session").status_code == 204
        assert reviewer.get("/api/v1/session").status_code == 401

    with TestClient(app) as after_reload:
        tasks = {task["id"]: task for task in after_reload.get("/api/v1/tasks").json()}
        assert tasks["LT-21"]["status"] == "done"
        assert tasks["LT-22"]["status"] == "todo"
