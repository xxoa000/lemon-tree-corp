"""가입, 자격 증명 복구와 모의 채용의 주요 흐름을 검증합니다."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

PASSWORD = "original-password"
RESUME = (
    "FastAPI 프로젝트에서 조회 API를 개발했습니다. 요청 유효성 검사와 오류 응답을 구현하고 "
    "테스트를 추가하여 정상과 실패 케이스를 검증했습니다."
)
ANSWERS = (
    "없는 리소스는 404, 잘못된 입력은 422로 응답하고 정상과 오류 응답을 테스트합니다.",
    "멱등 키의 unique 제약을 설정하고 트랜잭션 내부에서 충돌 시 기존 결과를 반환합니다.",
    "코드 리뷰 의견을 경청하고 대안을 제안했습니다. 합의 결과 오류 처리가 개선되었습니다.",
    "영향과 원인을 먼저 파악한 뒤 팀에 공유하고 우선순위와 분할 가능한 범위 등 대안을 제시하겠습니다.",
)


def register(client: TestClient, username: str) -> str:
    """테스트 계정을 등록하고 복구 코드를 반환합니다."""
    response = client.post(
        "/api/v1/accounts",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()["recovery_code"]


def login(client: TestClient, username: str, password: str = PASSWORD):
    """테스트 클라이언트에서 로그인 요청을 보냅니다."""
    return client.post(
        "/api/v1/session", json={"username": username, "password": password}
    )


def test_account_recovery_rotates_credentials(tmp_path, monkeypatch):
    """등록, 복구 검증, 비밀번호 변경과 이전 세션 무효화를 검증합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "accounts.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "test-only-account-secret-32-characters")
    with TestClient(app) as client:
        code = register(client, "candidate")
        assert login(client, "candidate").status_code == 200
        previous_token = client.cookies.get("lemontree_session")
        recovery = {"email": "candidate@example.com", "recovery_code": code}
        assert client.post("/api/v1/accounts/find", json=recovery).json() == {
            "username": "candidate"
        }
        reset = client.post(
            "/api/v1/accounts/reset",
            json={**recovery, "password": "replacement-password"},
        )
        assert reset.status_code == 200
        assert reset.json()["recovery_code"] != code
        assert client.post("/api/v1/accounts/find", json=recovery).status_code == 400
        assert login(client, "candidate").status_code == 401
        client.cookies.set("lemontree_session", previous_token)
        assert client.get("/api/v1/session").status_code == 401
        assert login(client, "candidate", "replacement-password").status_code == 200


def test_interview_and_reapplication(tmp_path, monkeypatch):
    """지원 실패·재지원·두 차례 면접·소유권 확인을 검증합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "test-only-account-secret-32-characters")
    with TestClient(app) as client:
        url = "/api/v1/jobs/applications"
        assert (
            client.get("/api/v1/jobs/posting").json()["title"] == "주니어 백엔드 개발자"
        )
        assert client.get(url).status_code == 401
        register(client, "candidate")
        assert login(client, "candidate").status_code == 200
        rejected = client.post(
            url, files={"resume": ("short.txt", b"hello", "text/plain")}
        ).json()
        assert rejected["stage"] == "screen_failed"

        file = {"resume": ("resume.txt", RESUME.encode(), "text/plain")}
        technical_fail = client.post(url, files=file).json()
        endpoint = f"{url}/{technical_fail['id']}/answers"
        for _ in range(2):
            technical_fail = client.post(
                endpoint,
                json={
                    "question_id": technical_fail["question"]["id"],
                    "answer": "모르겠습니다",
                },
            ).json()
        assert technical_fail["stage"] == "technical_failed"

        row = client.post(url, files=file).json()
        endpoint = f"{url}/{row['id']}/answers"
        assert row["stage"] == "technical"
        assert "FastAPI 프로젝트" in row["question"]["prompt"]
        assert (
            client.post(
                endpoint, json={"question_id": "invalid", "answer": ANSWERS[0]}
            ).status_code
            == 409
        )
        for answer, stage in zip(
            ANSWERS, ["technical", "behavioral", "behavioral", "hired"], strict=True
        ):
            row = client.post(
                endpoint, json={"question_id": row["question"]["id"], "answer": answer}
            ).json()
            assert row["stage"] == stage
        assert row["question"] is None
        assert len(client.get(url).json()) == 3

        register(client, "another")
        assert login(client, "another").status_code == 200
        assert client.get(url).json() == []
        assert (
            client.post(
                endpoint, json={"question_id": "tech-api", "answer": ANSWERS[0]}
            ).status_code
            == 404
        )


@pytest.mark.parametrize(
    ("role", "prefix", "technical_answers"),
    [
        (
            "frontend",
            "front",
            (
                "AbortController로 이전 요청을 취소하고 로딩과 오류 상태를 표시하며 재시도를 제공합니다.",
                "포커스 이동을 제한하고 Escape로 닫은 뒤 키보드를 사용하는 회귀 테스트를 추가합니다.",
            ),
        ),
        (
            "fullstack",
            "full",
            (
                "요청 스키마 계약을 정하고 유효성 오류와 서버 오류를 각 응답 상태 코드에 따라 구분합니다.",
                "로딩 중 버튼을 비활성화하고 멱등 키와 트랜잭션으로 동시 제출의 충돌을 처리합니다.",
            ),
        ),
        (
            "ai",
            "ai",
            (
                "검색 결과의 관련성과 답변 근거 및 출처를 검증하고 근거가 없으면 답변을 보류합니다.",
                "기준 모델과 동일한 평가 데이터셋으로 비교하고 운영에서 품질 지표를 모니터링합니다.",
            ),
        ),
    ],
)
@pytest.mark.parametrize("expected", ["hired", "behavioral_failed"])
def test_role_specific_final_results(
    tmp_path, monkeypatch, role, prefix, technical_answers, expected
):
    """추가 직무별 기술 면접과 인성 면접을 거쳐 합격 및 불합격을 검증합니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "roles.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "test-only-account-secret-32-characters")
    with TestClient(app) as client:
        postings = client.get("/api/v1/jobs/postings").json()
        assert {item["role"] for item in postings} == {
            "backend",
            "frontend",
            "fullstack",
            "ai",
        }
        register(client, "candidate")
        assert login(client, "candidate").status_code == 200
        upload = {"resume": ("resume.txt", RESUME.encode(), "text/plain")}
        url = "/api/v1/jobs/applications"
        assert (
            client.post(url, data={"role": "unknown"}, files=upload).status_code == 422
        )
        response = client.post(url, data={"role": role}, files=upload)
        assert response.status_code == 201
        row = response.json()
        assert row["role"] == role
        endpoint = f"{url}/{row['id']}/answers"
        for answer in technical_answers:
            assert row["question"]["id"].startswith(prefix + "-")
            response = client.post(
                endpoint, json={"question_id": row["question"]["id"], "answer": answer}
            )
            assert response.status_code == 200
            row = response.json()

        assert row["stage"] == "behavioral"
        for answer in (
            ANSWERS[2:] if expected == "hired" else ("모르겠습니다", "모르겠습니다")
        ):
            response = client.post(
                endpoint, json={"question_id": row["question"]["id"], "answer": answer}
            )
            assert response.status_code == 200
            row = response.json()
        assert row["stage"] == expected
        assert row["question"] is None
        assert client.get(url).json()[0] == row


def test_mock_interview_without_resume(tmp_path, monkeypatch):
    """개인정보 업로드 없이 기술 및 인성 면접을 완료할 수 있습니다."""
    monkeypatch.setenv("WORKPLACE_DB_PATH", str(tmp_path / "no-resume.sqlite3"))
    monkeypatch.setenv("WORKPLACE_JWT_SECRET", "test-only-account-secret-32-characters")
    with TestClient(app) as client:
        register(client, "candidate")
        assert login(client, "candidate").status_code == 200
        response = client.post("/api/v1/jobs/applications", data={"role": "backend"})
        assert response.status_code == 201
        row = response.json()
        assert row["stage"] == "technical"
        assert row["filename"] == ""
        assert "서류 심사를 건너뛰고" in row["feedback"]
        assert "이력서에서 확인한 내용" not in row["question"]["prompt"]
        path = f"/api/v1/jobs/applications/{row['id']}/answers"
        for answer in ANSWERS:
            row = client.post(
                path, json={"question_id": row["question"]["id"], "answer": answer}
            ).json()
        assert row["stage"] == "hired"
