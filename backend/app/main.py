"""LemonTree Corp phase-one API."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="LemonTree Corp API", version="0.1.0")

class Employee(BaseModel):
    id: str
    name: str
    team: str
    rank: str
    job_title: str
    specialty: str
    is_ai: bool = True

EMPLOYEES = [
    Employee(id="LT-001", name="차민석", team="경영진", rank="대표이사", job_title="CEO", specialty="경영 전략·사업 운영"),
    Employee(id="LT-002", name="강도윤", team="개발팀", rank="기술이사", job_title="CTO / 개발팀장", specialty="시스템 아키텍처·개발 표준"),
    Employee(id="LT-003", name="윤서진", team="디자인팀", rank="과장", job_title="PM / 디자인팀장", specialty="서비스 기획·프로젝트 관리"),
    Employee(id="LT-004", name="이준혁", team="개발팀", rank="과장", job_title="Senior Backend Engineer", specialty="FastAPI·Spring Boot·API"),
    Employee(id="LT-005", name="한유리", team="개발팀", rank="대리", job_title="Frontend Engineer", specialty="React·Next.js·TypeScript"),
    Employee(id="LT-006", name="박현우", team="개발팀", rank="부장", job_title="Senior Database Engineer", specialty="MySQL·데이터 모델링"),
    Employee(id="LT-007", name="최나린", team="디자인팀", rank="과장", job_title="Senior Product Designer", specialty="UI/UX·디자인 시스템"),
    Employee(id="LT-008", name="정하은", team="인프라팀", rank="차장", job_title="Senior QA Engineer / 인프라팀장", specialty="QA·자동화 테스트"),
    Employee(id="LT-009", name="오태민", team="인프라팀", rank="과장", job_title="Senior DevOps Engineer", specialty="Docker·Kubernetes·CI/CD"),
    Employee(id="LT-010", name="서지안", team="개발팀", rank="대리", job_title="AI / LLM Engineer", specialty="LLM·RAG·AI Agent"),
    Employee(id="LT-011", name="사용자", team="개발팀", rank="사원", job_title="Junior Backend Engineer", specialty="API·테스트·기술 학습", is_ai=False),
]

class Manager(BaseModel):
    id: str = "LT-SYS-001"
    name: str = "백서윤"
    rank: str = "부장"
    job_title: str = "AI Organization Manager"
    external_to_org: bool = True
    default_user_speech: str = "반말"
    invocation: str = "백서윤 부장님"
    invocation_semantics: str = "OWNER_DESIGN_REQUEST"

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/v1/employees", response_model=list[Employee])
def employees() -> list[Employee]:
    return EMPLOYEES

@app.get("/api/v1/teams")
def teams() -> list[dict[str, object]]:
    return [
        {"name": "디자인팀", "leader_id": "LT-003", "member_ids": ["LT-003", "LT-007"]},
        {"name": "개발팀", "leader_id": "LT-002", "member_ids": ["LT-002", "LT-004", "LT-005", "LT-006", "LT-010", "LT-011"]},
        {"name": "인프라팀", "leader_id": "LT-008", "member_ids": ["LT-008", "LT-009"]},
    ]

@app.get("/api/v1/control-center/manager", response_model=Manager)
def manager() -> Manager:
    return Manager()
