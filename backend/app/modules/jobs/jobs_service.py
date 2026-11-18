"""이력서 텍스트를 읽고 모의 선발의 질문과 단계를 관리합니다."""

from io import BytesIO
from pathlib import PurePath

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from .jobs_model import Application, InterviewAnswer
from .jobs_roles import AI, FRONTEND, FULLSTACK
from .jobs_schemas import Answer, ApplicationView, Posting, Question

MAX_SIZE = 2 * 1024 * 1024
MAX_PAGES = 10
TECH = (
    (
        "tech-api",
        "이준혁 과장 · 백엔드",
        "지원서에 나온 경험을 바탕으로 조회 API를 설계해 주세요. 존재하지 않는 리소스와 잘못된 입력에 어떻게 응답하고, 각각 어떻게 검증하겠습니까?",
        (
            ("404", "찾을 수 없"),
            ("400", "422", "유효성", "validation"),
            ("테스트", "test", "검증"),
        ),
    ),
    (
        "tech-db",
        "박현우 부장 · 데이터베이스",
        "같은 지원서를 두 번 제출하는 상황에서 API의 중복 처리 방식을 설계하고, 동시에 요청이 들어와도 일관성을 유지하는 방법을 설명해 주세요.",
        (
            ("고유", "unique", "유니크", "멱등", "idempot"),
            ("트랜잭션", "transaction", "원자"),
            ("충돌", "재시도", "중복", "409"),
        ),
    ),
)
CULT = (
    (
        "cult-feedback",
        "윤서진 과장 · 프로젝트 관리",
        "지원서에 나온 프로젝트를 예로 들어, 동료와 의견이 달랐던 상황이나 코드 리뷰 지적을 받은 상황에서 어떤 행동을 했고 결과가 어땠는지 설명해 주세요.",
        (
            ("의견", "경청", "질문", "피드백", "리뷰"),
            ("제안", "설명", "논의", "합의"),
            ("결과", "개선", "배웠", "변경"),
        ),
    ),
    (
        "cult-deadline",
        "이준혁 과장 · 백엔드",
        "마감일을 지키기 어려울 때, 무엇을 확인하고 누구에게 무엇을 공유하며 어떤 대안을 제시하겠습니까?",
        (
            ("공유", "알리", "보고", "소통"),
            ("이유", "원인", "일정", "영향"),
            ("우선순위", "대안", "범위", "분할"),
        ),
    ),
)
TECH_BY_ROLE = {"backend": TECH, "frontend": FRONTEND, "fullstack": FULLSTACK, "ai": AI}
ROLE_DETAILS = {
    "backend": (
        "주니어 백엔드 개발자",
        [
            "FastAPI 기반 API 개발과 테스트",
            "SQL 데이터 모델과 업무 서비스 개선",
            "코드 리뷰와 기술 문서 작성",
        ],
        "API 오류 처리·검증·테스트와 중복 요청·동시성",
    ),
    "frontend": (
        "주니어 프런트엔드 개발자",
        [
            "React·Next.js 화면 개발",
            "API 요청 상태와 오류 처리",
            "키보드 접근성 및 UI 테스트",
        ],
        "비동기 요청 상태 관리와 키보드 접근성",
    ),
    "fullstack": (
        "주니어 풀스택 개발자",
        [
            "React 화면과 FastAPI 연동",
            "요청·응답 계약과 입력 검증",
            "테스트 및 데이터 일관성 관리",
        ],
        "프런트엔드·API 계약과 중복 제출 방지",
    ),
    "ai": (
        "주니어 AI 엔지니어",
        [
            "문서 기반 질의응답 구현",
            "검색과 답변 품질 평가",
            "모델 비교 및 품질 모니터링",
        ],
        "문서 검색·답변 근거 확인과 모델 평가·모니터링",
    ),
}


def posting(role: str = "backend") -> Posting:
    """직무별 공고와 기술 평가 영역을 제공합니다."""
    title, duties, criteria = ROLE_DETAILS[role]
    return Posting(
        role=role,
        title=title,
        team="개발팀",
        duties=duties,
        criteria=criteria,
        format="서류 심사 → 1차 기술 면접 → 2차 인성 면접 → 최종 결과",
    )


def postings() -> list[Posting]:
    """공개 중인 모든 직무의 공고를 제공합니다."""
    return [posting(role) for role in ROLE_DETAILS]


def questions_for(row: Application):
    """지원 직무와 전형 단계에 해당하는 질문을 제공합니다."""
    if row.stage == "technical":
        return TECH_BY_ROLE[row.role]
    if row.stage == "behavioral":
        return CULT
    return ()


def read_resume(upload: UploadFile) -> tuple[str, str]:
    """텍스트 기반 PDF 또는 UTF-8 TXT 이력서를 정해진 크기 안에서 읽습니다."""
    filename = PurePath((upload.filename or "").replace(chr(92), "/")).name[:255]
    data = upload.file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "이력서는 최대 2MB까지 제출할 수 있습니다.")
    try:
        if filename.lower().endswith(".txt"):
            resume = data.decode("utf-8-sig")
        elif filename.lower().endswith(".pdf") and data.startswith(b"%PDF-"):
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
                raise HTTPException(
                    422, "암호가 없는 10페이지 이하 PDF를 제출해 주세요."
                )
            resume = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise HTTPException(415, "PDF 또는 UTF-8 TXT 이력서를 제출해 주세요.")
    except (UnicodeError, PdfReadError, ValueError, RecursionError) as error:
        raise HTTPException(422, "이력서를 읽지 못했습니다.") from error
    resume = "\n".join(line.strip() for line in resume.splitlines() if line.strip())[
        :24000
    ]
    if not resume or "\0" in resume:
        raise HTTPException(422, "읽을 수 있는 이력서 텍스트가 필요합니다.")
    return filename, resume


def application_view(db: Session, row: Application) -> ApplicationView:
    """현재 단계 및 아직 응답하지 않은 질문을 제공합니다."""
    answered = set(
        db.scalars(
            select(InterviewAnswer.question_id).where(
                InterviewAnswer.application_id == row.id
            ),
        )
    )
    question = None
    for index, (key, interviewer, prompt, _) in enumerate(questions_for(row)):
        if key not in answered:
            if index == 0:
                lines = row.resume.splitlines()
                relevant = next(
                    (
                        line
                        for line in lines
                        if any(
                            word in line.lower()
                            for word in (
                                "api",
                                "프로젝트",
                                "백엔드",
                                "데이터베이스",
                                "python",
                            )
                        )
                    ),
                    lines[0],
                )
                prompt = f"이력서에서 확인한 내용: “{relevant[:180]}”\n\n{prompt}"
            question = Question(id=key, interviewer=interviewer, prompt=prompt)
            break
    return ApplicationView(
        id=row.id,
        role=row.role,
        filename=row.filename,
        stage=row.stage,
        feedback=row.feedback,
        created_at=row.created_at,
        question=question,
    )


def applications(engine: Engine, applicant: str) -> list[ApplicationView]:
    """로그인한 지원자의 이전 지원과 진행 중 상태를 응답합니다."""
    with Session(engine) as db:
        rows = db.scalars(
            select(Application)
            .where(Application.applicant == applicant)
            .order_by(Application.id.desc())
        )
        return [application_view(db, row) for row in rows]


def apply(
    engine: Engine, applicant: str, upload: UploadFile, role: str
) -> ApplicationView:
    """이력서를 검토하고 이전 지원 결과와 무관하게 새 지원을 생성합니다."""
    if role not in ROLE_DETAILS:
        raise HTTPException(422, "공고 직무를 확인해 주세요.")
    filename, resume = read_resume(upload)
    has_experience = any(
        word in resume.lower()
        for word in (
            "프로젝트",
            "project",
            "repository",
            "경험",
            "구현",
            "개발",
            "만들",
        )
    )
    passed = len(resume) >= 60 and has_experience
    with Session(engine) as db, db.begin():
        row = Application(
            applicant=applicant,
            role=role,
            filename=filename,
            resume=resume,
            stage="technical" if passed else "screen_failed",
            feedback=(
                "서류 통과 · 개발 경험이 확인되었습니다. 1차 기술 면접을 시작합니다."
                if passed
                else "서류 불합격 · 60자 이상의 이력서에 프로젝트와 본인의 기여를 구체적으로 적어 재지원해 주세요."
            ),
        )
        db.add(row)
        db.flush()
        return application_view(db, row)


def submit_answer(
    engine: Engine, applicant: str, application_id: int, data: Answer
) -> ApplicationView:
    """현재 질문의 응답을 평가하고 해당 전형의 마지막 질문이면 결과를 저장합니다."""
    answer = data.answer.strip()
    if not answer:
        raise HTTPException(422, "답변을 입력해 주세요.")
    with Session(engine) as db, db.begin():
        db.execute(text("BEGIN IMMEDIATE"))
        row = db.get(Application, application_id)
        if row is None or row.applicant != applicant:
            raise HTTPException(404, "지원 정보를 찾을 수 없습니다.")
        question = application_view(db, row).question
        if question is None or question.id != data.question_id:
            raise HTTPException(
                409, "현재 질문이 변경되었습니다. 지원 목록을 다시 확인해 주세요."
            )

        stage_questions = questions_for(row)
        index, rubric = next(
            (i, rubric)
            for i, (key, _, _, rubric) in enumerate(stage_questions)
            if key == question.id
        )
        score = (
            sum(any(keyword in answer.lower() for keyword in group) for group in rubric)
            if len(answer) >= 25
            else 0
        )
        db.add(
            InterviewAnswer(
                application_id=row.id,
                question_id=question.id,
                answer=answer,
                score=score,
            )
        )
        db.flush()
        if index == len(stage_questions) - 1:
            scores = list(
                db.scalars(
                    select(InterviewAnswer.score).where(
                        InterviewAnswer.application_id == row.id,
                        InterviewAnswer.question_id.in_(
                            [item[0] for item in stage_questions]
                        ),
                    )
                )
            )
            passed = sum(scores) >= 4 and min(scores) >= 1
            if row.stage == "technical":
                row.stage = "behavioral" if passed else "technical_failed"
                guidance = f"{ROLE_DETAILS[row.role][2]}에 대한 설명을 보강해 주세요."
                result = (
                    "기술 면접 통과 · 2차 인성 면접을 시작합니다."
                    if passed
                    else "기술 면접 불합격"
                )
            else:
                row.stage = "hired" if passed else "behavioral_failed"
                guidance = "협업 상황에서 취한 행동, 소통 대상과 결과를 구체적으로 설명해 주세요."
                result = "모의면접 최종 합격" if passed else "인성 면접 불합격"
            row.feedback = f"{result} ({sum(scores)}/6점)." + (
                f" {guidance}" if not passed else ""
            )
        return application_view(db, row)
