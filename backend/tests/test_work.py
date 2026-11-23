"""업무 요청부터 예산 예약, Codex 이벤트, 검토 패치까지 검증합니다."""

import os
import subprocess
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from app.main import app
from app.modules.auth.auth_seed import provision
from app.modules.work import work_runner, work_service


@pytest.mark.parametrize("with_images", [False, True])
def test_approved_work_runs_in_an_isolated_checkout(tmp_path, monkeypatch, with_images):
    """관리자 승인과 예산을 요구하고 작업 결과는 복제본에서만 수집합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "work-test-secret-at-least-32-bytes")

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "original.txt").write_text("baseline\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
    )

    executable = tmp_path / "codex"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import json, sys\n"
        "assert '작업 내용' in sys.stdin.read()\n"
        f"assert ('--image' in sys.argv) == {with_images!r}\n"
        "if '--image' in sys.argv:\n"
        "    paths = sys.argv[sys.argv.index('--image') + 1].split(',')\n"
        "    assert len(paths) == 2\n"
        "    assert all(Path(path).read_bytes().startswith(bytes.fromhex('89504e470d0a1a0a')) for path in paths)\n"
        "Path('generated.txt').write_text('new work\\n')\n"
        "print(json.dumps({'type': 'item.completed', 'item': {'type': 'file_change'}}), flush=True)\n"
        "print(json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'verified'}}))\n"
        "print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 23, 'output_tokens': 5}}))\n"
    )
    executable.chmod(0o700)
    url = "/api/v1/codex-work"
    with TestClient(app) as client:
        engine = app.state.workplace_engine
        assert client.get(url).status_code == 401
        member = {"username": "membertest", "password": "password-1234"}
        assert (
            client.post(
                "/api/v1/accounts", json={**member, "email": "member@example.com"}
            ).status_code
            == 201
        )
        assert client.post("/api/v1/session", json=member).status_code == 200
        assert client.get(url).status_code == 403
        username, _ = provision(engine, "LT-SYS-001", "password-1234")
        assert (
            client.post(
                "/api/v1/session",
                json={"username": username, "password": "password-1234"},
            ).status_code
            == 200
        )
        dashboard = client.get(url).json()
        staff = next(
            person for person in dashboard["staff"] if person["id"] == "LT-007"
        )
        draft = {"employee_id": staff["id"], "title": "UI", "prompt": "작업 내용"}
        if with_images:
            buffer = BytesIO()
            Image.new("RGB", (10, 10), "green").save(buffer, "JPEG")
            uploaded = [
                ("images", ("reference.jpg", buffer.getvalue(), "image/jpeg")),
                ("images", ("clipboard.jpg", buffer.getvalue(), "image/jpeg")),
            ]
            assert (
                client.post(
                    url + "/with-images",
                    data=draft,
                    files=[("images", ("bad.png", b"fake", "image/png"))],
                ).status_code
                == 422
            )
            created = client.post(url + "/with-images", data=draft, files=uploaded)
        else:
            created = client.post(url, json=draft)
        assert created.status_code == 201
        assert work_service.claim(engine) is None
        assignment = f"{url}/{created.json()['id']}"
        if with_images:
            assert created.json()["images"] == [
                {"position": 1, "name": "reference.jpg"},
                {"position": 2, "name": "clipboard.jpg"},
            ]
            image = client.get(assignment + "/images/1")
            assert image.headers["content-type"] == "image/png"
            assert image.headers["cache-control"] == "private, no-store"
            assert Image.open(BytesIO(image.content)).size == (10, 10)
        for _ in range(2):
            assert client.post(assignment + "/approve").json()["state"] == "queued"
        after = client.get(url).json()
        remaining = next(
            person["remaining"]
            for person in after["staff"]
            if person["id"] == staff["id"]
        )
        assert remaining == staff["remaining"] - dashboard["charge"]
        work = work_service.claim(engine)
        assert work and work.state == "running"
        assert work_service.claim(engine) is None
        work_runner.execute(
            engine, work, repo, str(executable), {"PATH": os.environ["PATH"]}
        )
        result = client.get(url).json()["jobs"][0]
        assert result["state"] == "review"
        assert result["tokens"] == 28 and result["summary"] == "verified"
        assert result["has_patch"]
        assert len(result["images"]) == (2 if with_images else 0)
        assert "+new work" in client.get(assignment + "/patch").text
        assert not (repo / "generated.txt").exists()
        with engine.connect() as db:
            assert list(db.scalars(text("SELECT state FROM llm_usage"))) == ["settled"]
        if with_images:
            assert client.delete("/api/v1/session").status_code == 204
            assert client.get(assignment + "/images/1").status_code == 401
