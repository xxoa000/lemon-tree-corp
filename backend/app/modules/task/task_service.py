"""업무 조회와 담당자 권한을 확인한 상태 변경을 처리합니다."""

from fastapi import HTTPException
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from .task_model import Task, TaskEvent
from .task_schemas import Status, TaskResponse


def list_tasks(engine: Engine) -> list[TaskResponse]:
    """업무 목록을 업무 식별자 내림차순으로 조회합니다."""
    with Session(engine) as session:
        return [
            TaskResponse.model_validate(task)
            for task in session.scalars(select(Task).order_by(Task.id.desc()))
        ]


def update_status(engine: Engine, task_id: str, employee_id: str, status: Status) -> TaskResponse:
    """담당자의 상태 변경과 변경 전후 이력을 한 트랜잭션으로 저장합니다."""
    with Session(engine) as session, session.begin():
        session.execute(text("BEGIN IMMEDIATE"))
        task = session.get(Task, task_id)
        if task is None:
            raise HTTPException(404, "업무를 찾을 수 없습니다.")
        if task.assignee_id != employee_id:
            raise HTTPException(403, "본인에게 배정된 업무만 변경할 수 있습니다.")
        if task.status != status:
            session.add(TaskEvent(
                task_id=task.id, actor_id=employee_id, previous_status=task.status, status=status,
            ))
            task.status = status
        return TaskResponse.model_validate(task)
