"""로컬 평가 API의 요청, 응답 검증과 클라우드 차단을 테스트합니다."""

import json
import os

import httpx
import pytest
from app.modules.jobs import jobs_evaluator
from fastapi import HTTPException

CRITERIA = ("없는 항목 처리", "잘못된 입력 처리", "검증 계획")
ANSWER = "없는 항목은 찾을 수 없다고 답하고, 잘못된 입력은 사용자에게 알려 줍니다."


def transport(monkeypatch, evidence):
    """로컬 Ollama와 동일한 HTTP 형식의 검증용 응답을 반환합니다."""
    real_client = httpx.Client

    def reply(request):
        assert request.url.host == "127.0.0.1"
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["format"]["properties"]["criteria"]["minItems"] == 3
        payload = json.loads(body["messages"][1]["content"])
        assert payload["candidate_answer"] == ANSWER
        assert payload["interviewer_role"] == "이준혁 과장 · 백엔드"
        assert "담백하고 직접적인 실무형" in payload["feedback_style"]
        assert (
            "Grade independently of the interviewer style"
            in body["messages"][0]["content"]
        )
        return httpx.Response(
            200,
            json={
                "done": True,
                "message": {
                    "content": json.dumps(
                        {
                            "criteria": [
                                {"met": True, "evidence": evidence},
                                {"met": False, "evidence": "ignored"},
                                {"met": False, "evidence": ""},
                            ],
                            "feedback": "오류를 구분한 건 좋아요. 제가 API를 운영한다면 두 경우를 각각 테스트해 볼 것 같아요.",
                            "corrections": [
                                {
                                    "quote": "사용자에게 알려 줍니다",
                                    "correction": "오류 응답을 구체화하세요.",
                                }
                            ],
                            "model_answer": "존재하지 않으면 404를, 입력이 잘못되면 422를 응답합니다.",
                        }
                    )
                },
            },
        )

    monkeypatch.setattr(
        jobs_evaluator.httpx,
        "Client",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(reply),
            **kwargs,
        ),
    )


def test_valid_evidence_sets_score(monkeypatch):
    """응답의 근거를 원문과 대조하고 점수를 서버에서 합산합니다."""
    monkeypatch.setenv("INTERVIEW_OLLAMA_URL", "http://127.0.0.1:11434")
    transport(monkeypatch, "찾을 수 없다고 답하고")
    result = jobs_evaluator.evaluate("tech-api", "질문", CRITERIA, ANSWER)
    assert result.score == 1
    assert "제가 API를 운영한다면" in result.feedback
    assert result.criteria[1].evidence == ""
    assert result.corrections[0].quote in ANSWER
    assert "404" in result.model_answer


def test_all_interviewers_have_distinct_styles():
    """실제 문항에 배정된 담당자마다 고유한 말투가 설정되어 있는지 확인합니다."""
    names = {label.split(" · ", 1)[0] for label in jobs_evaluator.INTERVIEWERS.values()}
    assert names == jobs_evaluator.FEEDBACK_STYLES.keys()
    assert len(set(jobs_evaluator.FEEDBACK_STYLES.values())) == len(names)


def test_hallucinated_quote_stops_grading(monkeypatch):
    """원문에 없는 인용은 결과를 보류합니다."""
    monkeypatch.setenv("INTERVIEW_OLLAMA_URL", "http://127.0.0.1:11434")
    transport(monkeypatch, "원문에 없는 인용")
    with pytest.raises(HTTPException) as error:
        jobs_evaluator.evaluate("tech-api", "질문", CRITERIA, ANSWER)
    assert error.value.status_code == 503


@pytest.mark.parametrize(
    ("url", "model"),
    [
        ("https://ollama.com", "qwen2.5:3b"),
        ("http://127.0.0.1:11434", "qwen3:cloud"),
    ],
)
def test_remote_configuration_is_rejected(monkeypatch, url, model):
    """외부 서버 또는 클라우드 모델 설정을 거부합니다."""
    monkeypatch.setenv("INTERVIEW_OLLAMA_URL", url)
    monkeypatch.setenv("INTERVIEW_OLLAMA_MODEL", model)
    with pytest.raises(HTTPException) as error:
        jobs_evaluator.local_settings()
    assert error.value.status_code == 503


@pytest.mark.skipif(
    os.getenv("TEST_LOCAL_OLLAMA") != "1",
    reason="별도의 로컬 Ollama와 모델이 필요합니다.",
)
def test_real_ollama_distinguishes_meaning_from_keywords():
    """실제 설치한 모델이 맞는 설명과 키워드만 맞는 답안을 구분하는지 확인합니다."""
    from app.modules.jobs.jobs_roles import TECH

    key, _, question, criteria = TECH[0]
    explanation = (
        "대상이 없으면 요청한 항목을 찾을 수 없다고 답합니다. 형식이 틀린 값은 입력을 보낸 쪽이 "
        "고칠 수 있게 별도 오류를 반환합니다. 각각의 잘못된 요청을 직접 보내 응답을 자동으로 비교합니다."
    )
    keyword_only = (
        "존재하지 않는 리소스는 422로 처리하고 잘못된 입력은 404로 보냅니다. "
        "테스트라고 적지만 실제로는 성공 사례만 확인하겠습니다."
    )
    assert jobs_evaluator.evaluate(key, question, criteria, explanation).score >= 2
    assert jobs_evaluator.evaluate(key, question, criteria, keyword_only).score <= 1
