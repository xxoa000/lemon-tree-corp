"""업무 목록 조회와 담당자 상태 변경 경로를 등록합니다."""

from fastapi import APIRouter, Depends, Request, Response

from app.modules.auth.auth_router import session_employee

from . import task_service
from .task_schemas import TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/v1")


@router.get("/tasks")
def tasks(request: Request, response: Response) -> list[TaskResponse]:
    """업무 보드의 업무 목록을 응답합니다."""
    response.headers["Cache-Control"] = "no-store"
    return task_service.list_tasks(request.app.state.workplace_engine)


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str, update: TaskUpdate, request: Request, employee_id: str = Depends(session_employee),
) -> TaskResponse:
    """인증된 담당자의 업무 상태 변경 요청을 처리합니다."""
    return task_service.update_status(
        request.app.state.workplace_engine, task_id, employee_id, update.status,
    )
