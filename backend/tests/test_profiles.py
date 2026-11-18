"""회원정보, 프로필 사진과 직원 권한을 검증합니다."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.database import create_workplace_engine
from app.main import app
from app.modules.auth.auth_seed import provision

PASSWORD = "local-test-password"


def test_member_profile_and_avatar(tmp_path, monkeypatch):
    """신규 계정이 사원으로 가입하고 자기 정보와 사진만 관리하는지 확인합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "profile.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "local-test-only-32-byte-signing-secret")
    with TestClient(app) as client:
        assert client.get("/api/v1/accounts/me").status_code == 401
        credentials = {"username": "worker", "password": PASSWORD}
        assert (
            client.post(
                "/api/v1/accounts",
                json={
                    **credentials,
                    "email": "worker@example.com",
                },
            ).status_code
            == 201
        )
        assert (
            client.post("/api/v1/session", json=credentials).json()["role"] == "member"
        )
        profile = {
            "display_name": "유저",
            "email": "new@example.com",
            "phone": "010-0000-0000",
            "bio": "API 개발",
        }
        assert (
            client.patch(
                "/api/v1/accounts/me", json={**profile, "role": "admin"}
            ).status_code
            == 422
        )
        assert client.patch("/api/v1/accounts/me", json=profile).status_code == 200
        saved = client.get("/api/v1/accounts/me").json()
        assert {key: saved[key] for key in profile} == profile
        assert "password_hash" not in saved
        assert client.get("/api/v1/accounts/staff").status_code == 403
        url = "/api/v1/accounts/me/avatar"
        assert client.get(url).status_code == 404
        assert (
            client.put(
                url, files={"image": ("bad.png", b"invalid", "image/png")}
            ).status_code
            == 422
        )
        buffer = BytesIO()
        Image.new("RGB", (600, 300), "green").save(buffer, "PNG")
        assert (
            client.put(
                url, files={"image": ("profile.png", buffer.getvalue(), "image/png")}
            ).status_code
            == 204
        )
        response = client.get(url)
        assert response.headers["content-type"] == "image/webp"
        assert Image.open(BytesIO(response.content)).size == (512, 256)
        assert client.get("/api/v1/accounts/me").json()["has_avatar"] is True
        assert client.delete("/api/v1/session").status_code == 204
        assert client.get(url).status_code == 401


def test_staff_admin_seed(tmp_path, monkeypatch):
    """백서윤 계정만 관리자이며 시드 계정의 자격 증명 설정 후 로그인되는지 확인합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "staff.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "local-test-only-32-byte-signing-secret")
    with TestClient(app) as client:
        credentials = {"username": "staff:lt-sys-001", "password": PASSWORD}
        assert client.post("/api/v1/session", json=credentials).status_code == 401
        engine = create_workplace_engine()
        try:
            assert len(provision(engine, "LT-SYS-001", PASSWORD)) >= 20
            provision(engine, "LT-011", PASSWORD)
        finally:
            engine.dispose()

        result = client.post("/api/v1/session", json=credentials).json()
        assert result["role"] == "admin"
        assert result["org_employee_id"] == "LT-SYS-001"
        staff = client.get("/api/v1/accounts/staff").json()
        assert len(staff) == 12
        assert [row["employee_id"] for row in staff if row["role"] == "admin"] == [
            "LT-SYS-001"
        ]
        assert client.get("/api/v1/accounts/me").json()["display_name"] == "백서윤"
        assert (
            client.post(
                "/api/v1/session", json={**credentials, "username": "staff:lt-011"}
            ).json()["role"]
            == "member"
        )
        assert (
            client.patch("/api/v1/tasks/LT-21", json={"status": "done"}).status_code
            == 200
        )
        assert client.get("/api/v1/accounts/staff").status_code == 403
