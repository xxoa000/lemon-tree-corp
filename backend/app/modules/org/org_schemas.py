"""직원과 외부 관리자 API의 응답 구조를 정의합니다."""

from pydantic import BaseModel


class Employee(BaseModel):
    """조직도에 표시하는 직원 정보를 정의합니다."""

    id: str
    name: str
    team: str
    rank: str
    job_title: str
    specialty: str
    is_ai: bool = True

class Manager(BaseModel):
    """조직 외부 시스템 관리자 정보를 정의합니다."""

    id: str = "LT-SYS-001"
    name: str = "백서윤"
    rank: str = "부장"
    job_title: str = "AI Organization Manager"
    external_to_org: bool = True
    default_user_speech: str = "반말"
    invocation: str = "백서윤 부장님"
    invocation_semantics: str = "OWNER_DESIGN_REQUEST"
