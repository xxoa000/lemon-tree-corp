"""FastAPI 애플리케이션과 기능별 API 라우터를 구성합니다."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from app.database import create_workplace_engine, upgrade_workplace
from app.modules.auth.auth_router import router as auth_router
from app.modules.cv.cv_router import router as cv_router
from app.modules.jobs.jobs_router import router as jobs_router
from app.modules.llm.llm_router import router as llm_router
from app.modules.org.org_router import router as org_router
from app.modules.talk.talk_router import router as talk_router
from app.modules.task.task_router import router as task_router
from app.modules.vlog.vlog_router import router as vlog_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """서버 시작 시 DB를 업그레이드하고 종료 시 연결을 정리합니다."""
    engine = create_workplace_engine()
    try:
        upgrade_workplace(engine)
        app.state.workplace_engine = engine
        yield
    finally:
        engine.dispose()


app = FastAPI(title="LemonTree Corp API", version="0.1.0", lifespan=lifespan)
app.include_router(org_router)
app.include_router(auth_router)
app.include_router(vlog_router)
app.include_router(talk_router)
app.include_router(cv_router)
app.include_router(jobs_router)
app.include_router(llm_router)
app.include_router(task_router)


@app.get("/health")
def health() -> dict[str, str]:
    """애플리케이션의 응답 상태를 확인합니다."""
    return {"status": "ok"}


@app.exception_handler(RedisError)
async def redis_unavailable(request: Request, error: RedisError) -> JSONResponse:
    """Redis 연결 오류를 채팅 일시 불가로 응답합니다."""
    return JSONResponse({"detail": "LemonTalk 저장소에 연결할 수 없습니다."}, status_code=503)
