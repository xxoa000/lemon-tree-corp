"""이력서 접근 권한, LemonTalk 읽음·멤버십, TechVlog CRUD를 검증합니다."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def clients(tmp_path, monkeypatch):
    """서로 다른 세 계정을 같은 로컬 DB에 로그인합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "workspace.sqlite3"))
    monkeypatch.setenv(
        "WORKPLACE_JWT_SECRET", "workspace-test-secret-at-least-32-bytes"
    )
    with TestClient(app) as first, TestClient(app) as second, TestClient(app) as third:
        for name, client in zip(
            ("alice", "bobby", "carol"), (first, second, third), strict=True
        ):
            credentials = {"username": name, "password": "fixture-password"}
            assert (
                client.post(
                    "/api/v1/accounts",
                    json={
                        **credentials,
                        "email": f"{name}@example.com",
                    },
                ).status_code
                == 201
            )
            assert client.post("/api/v1/session", json=credentials).status_code == 200
        yield first, second, third


def test_resume_original_and_edits_are_private(clients):
    """원본과 편집본이 독립적으로 저장되며 다른 계정에서 보이지 않습니다."""
    alice, bobby, _ = clients
    url = "/api/v1/accounts/me/resume"
    data = b"Worked on an API project."
    assert alice.put(url + "/file", files={"file": ("resume.txt", data)}).json() == {
        "filename": "resume.txt",
        "content": data.decode(),
    }
    assert (
        alice.patch(url, json={"content": "Updated project description"}).status_code
        == 200
    )
    assert alice.get(url).json()["content"] == "Updated project description"
    assert alice.get(url + "/file").content == data
    assert "attachment" in alice.get(url + "/file").headers["Content-Disposition"]
    assert bobby.get(url).json() is None
    assert bobby.get(url + "/file").status_code == 404


def test_direct_chat_team_members_and_unread(clients):
    """개인·팀 메시지는 참여자에게만 보이고 읽은 메시지만 집계에서 빠집니다."""
    alice, bobby, carol = clients
    talk = "/api/v1/talk"
    ids = {row["name"]: row["id"] for row in alice.get(talk + "/contacts").json()}
    bob = ids["bobby"]
    alice_id = next(
        row["id"]
        for row in bobby.get(talk + "/contacts").json()
        if row["name"] == "alice"
    )
    dm = alice.post(talk + "/dm", json={"contact": bob}).json()["id"]
    assert bobby.post(talk + "/dm", json={"contact": alice_id}).json()["id"] == dm
    url = f"{talk}/rooms/{dm}"
    message = alice.post(url + "/messages", json={"body": "Hello"}).json()["id"]
    assert carol.get(url).status_code == 404
    assert carol.post(url + "/messages", json={"body": "blocked"}).status_code == 404
    assert bobby.get(talk + "/rooms").json()[0]["unread"] == 1
    assert bobby.get(url).json()["messages"][0]["body"] == "Hello"
    assert bobby.post(url + "/read", json={"message_id": message}).status_code == 204
    assert bobby.get(talk + "/rooms").json()[0]["unread"] == 0
    group = alice.post(
        talk + "/groups", json={"name": "개발팀 방", "team": "개발팀"}
    ).json()["id"]
    url = f"{talk}/rooms/{group}"
    assert (
        alice.post(url + "/messages", json={"body": "before invite"}).status_code == 201
    )
    assert alice.put(f"{url}/members/{bob}").status_code == 204
    assert bobby.get(url).json()["messages"] == []
    assert bobby.put(f"{url}/members/{ids['carol']}").status_code == 403
    assert (
        bobby.post(url + "/messages", json={"body": "team message"}).status_code == 201
    )
    assert alice.get(url).json()["messages"][-1]["body"] == "team message"
    assert alice.delete(f"{url}/members/{bob}").status_code == 204
    assert bobby.get(url).status_code == 404
    assert all(room["id"] != group for room in bobby.get(talk + "/rooms").json())


def test_vlog_has_release_notes_and_author_crud(clients):
    """Markdown 릴리스와 작성자 전용 게시글 변경을 검증합니다."""
    alice, bobby, _ = clients
    url = "/api/v1/vlog"
    assert any(row["id"].startswith("release:") for row in alice.get(url).json())
    draft = {"title": "업데이트", "body": "**Markdown**"}
    response = alice.post(url, json=draft)
    assert response.status_code == 201
    target = url + "/" + response.json()["id"]
    assert bobby.patch(target, json={**draft, "title": "blocked"}).status_code == 403
    assert bobby.delete(target).status_code == 403
    assert (
        alice.patch(target, json={**draft, "title": "edited"}).json()["title"]
        == "edited"
    )
    assert alice.delete(target).status_code == 204
    assert all(row["id"] != response.json()["id"] for row in alice.get(url).json())
