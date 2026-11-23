"""면접과 LemonTalk에서 공유하는 로컬 Ollama 호출을 처리합니다."""

import json
import os
from threading import BoundedSemaphore
from typing import TypeVar
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "host.docker.internal", "ollama"}
LOCAL_MODELS = {"qwen2.5:3b", "qwen2.5:7b"}
SLOTS = BoundedSemaphore(1)


class OllamaBusy(HTTPException):
    """로컬 모델을 다른 요청이 사용 중입니다."""


def local_settings() -> tuple[str, str]:
    """로컬 주소와 지원하는 다운로드형 모델만 허용합니다."""
    endpoint = os.getenv("INTERVIEW_OLLAMA_URL", "http://127.0.0.1:11434")
    model = os.getenv("INTERVIEW_OLLAMA_MODEL", "qwen2.5:7b")
    try:
        parsed = urlsplit(endpoint)
        valid = (
            parsed.scheme == "http"
            and parsed.hostname in LOCAL_HOSTS
            and parsed.port != 0
            and not parsed.username
            and not parsed.password
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        valid = False
    if not valid or model not in LOCAL_MODELS:
        raise HTTPException(503, "로컬 Ollama 주소와 지원 모델 설정을 확인해 주세요.")
    return endpoint.rstrip("/"), model


Schema = TypeVar("Schema", bound=BaseModel)


def local_json(
    system: str, data: dict, schema: type[Schema], *, max_tokens: int = 1000
) -> Schema:
    """로컬 Ollama에 정해진 JSON 계약으로 요청합니다."""
    endpoint, model = local_settings()
    if not SLOTS.acquire(blocking=False):
        raise OllamaBusy(
            503, "로컬 모델이 다른 요청을 처리 중입니다. 잠시 뒤 다시 시도해 주세요."
        )
    try:
        with httpx.Client(
            timeout=httpx.Timeout(120, connect=3), trust_env=False
        ) as client:
            response = client.post(
                f"{endpoint}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": schema.model_json_schema(),
                    "options": {
                        "temperature": 0,
                        "seed": 42,
                        "num_ctx": 8192,
                        "num_predict": max_tokens,
                    },
                    "messages": [
                        {"role": "system", "content": system},
                        {
                            "role": "user",
                            "content": json.dumps(data, ensure_ascii=False),
                        },
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("done") or payload.get("done_reason") == "length":
                raise ValueError("Incomplete model output")
            return schema.model_validate_json(payload["message"]["content"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise HTTPException(
            503,
            "로컬 Ollama 응답을 완료하지 못했습니다. 모델 실행 상태를 확인한 뒤 다시 시도해 주세요.",
        ) from error
    finally:
        SLOTS.release()
