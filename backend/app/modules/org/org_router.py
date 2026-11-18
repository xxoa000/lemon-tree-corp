"""직원, 팀, 외부 시스템 관리자 조회 경로를 등록합니다."""

from fastapi import APIRouter

from . import org_service
from .org_schemas import Employee, Manager

router = APIRouter(prefix="/api/v1")


@router.get("/employees", response_model=list[Employee])
def employees() -> list[Employee]:
    """직원 목록을 응답합니다."""
    return org_service.employees()


@router.get("/teams")
def teams() -> list[dict[str, object]]:
    """팀 목록과 각 팀의 구성원을 응답합니다."""
    return org_service.teams()


@router.get("/control-center/manager", response_model=Manager)
def manager() -> Manager:
    """백서윤 외부 시스템 관리자 프로필을 응답합니다."""
    return org_service.manager()
