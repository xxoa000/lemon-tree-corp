"""FastAPI 애플리케이션과 기능별 API 라우터를 구성합니다."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_workplace_engine, upgrade_workplace
from app.modules.auth.auth_router import router as auth_router
from app.modules.org.org_router import router as org_router
from app.modules.task.task_router import router as task_router


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
app.include_router(task_router)


@app.get("/health")
def health() -> dict[str, str]:
    """애플리케이션의 응답 상태를 확인합니다."""
    return {"status": "ok"}
