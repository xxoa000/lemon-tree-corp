"""이력서 텍스트를 읽고 모의 선발의 질문과 단계를 관리합니다."""

import json
import re
from io import BytesIO
from pathlib import PurePath

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.database import lock_sqlite_write

from .jobs_evaluator import evaluate, generate_question
from .jobs_model import Application, InterviewAnswer, InterviewQuestion
from .jobs_roles import AI, CULT, FRONTEND, FULLSTACK, TECH
from .jobs_schemas import (
    Answer,
    ApplicationView,
    Evaluation,
    InterviewEntry,
    InterviewHistory,
    Posting,
    Question,
)

MAX_SIZE = 2 * 1024 * 1024
MAX_PAGES = 10
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


def unanswered(db: Session, row: Application):
    """현재 전형에서 아직 답하지 않은 첫 번째 질문 슬롯을 반환합니다."""
    answered = set(
        db.scalars(
            select(InterviewAnswer.question_id).where(
                InterviewAnswer.application_id == row.id,
            )
        )
    )
    return next((item for item in questions_for(row) if item[0] not in answered), None)


def application_view(db: Session, row: Application) -> ApplicationView:
    """현재 전형과 저장된 다음 질문, 최근 평가를 반환합니다."""
    slot = unanswered(db, row)
    stored = db.get(InterviewQuestion, (row.id, slot[0])) if slot else None
    question = (
        Question(id=stored.question_id, interviewer=slot[1], prompt=stored.prompt)
        if stored and slot
        else None
    )
    latest = db.scalar(
        select(InterviewAnswer)
        .where(
            InterviewAnswer.application_id == row.id,
            InterviewAnswer.evaluation.is_not(None),
        )
        .order_by(InterviewAnswer.id.desc())
        .limit(1)
    )
    return ApplicationView(
        id=row.id,
        role=row.role,
        filename=row.filename,
        stage=row.stage,
        feedback=row.feedback,
        created_at=str(row.created_at),
        question=question,
        latest_evaluation=Evaluation.model_validate_json(latest.evaluation)
        if latest and latest.evaluation
        else None,
        latest_answer=latest.answer if latest else None,
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
    engine: Engine, applicant: str, upload: UploadFile | None, role: str
) -> ApplicationView:
    """이력서를 검토하고 이전 지원 결과와 무관하게 새 지원을 생성합니다."""
    if role not in ROLE_DETAILS:
        raise HTTPException(422, "공고 직무를 확인해 주세요.")
    filename, resume = read_resume(upload) if upload and upload.filename else ("", "")
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
    passed = not filename or (len(resume) >= 60 and has_experience)
    with Session(engine) as db, db.begin():
        row = Application(
            applicant=applicant,
            role=role,
            filename=filename,
            resume=resume,
            stage="technical" if passed else "screen_failed",
            feedback=(
                "이력서 없이 연습합니다. 서류 심사를 건너뛰고 1차 기술 면접을 시작합니다."
                if not filename
                else "서류 통과 · 개발 경험이 확인되었습니다. 1차 기술 면접을 시작합니다."
                if passed
                else "서류 불합격 · 60자 이상의 이력서에 프로젝트와 본인의 기여를 구체적으로 적어 재지원해 주세요."
            ),
        )
        db.add(row)
        db.flush()
        return application_view(db, row)


def owned_application(
    db: Session, application_id: int, applicant: str, *, lock: bool = False
) -> Application:
    """지원 소유자가 맞을 때만 해당 지원 건을 반환합니다."""
    row = db.get(Application, application_id, with_for_update=lock)
    if row is None or row.applicant != applicant:
        raise HTTPException(404, "지원 정보를 찾을 수 없습니다.")
    return row


def prepare_question(
    engine: Engine, applicant: str, application_id: int
) -> ApplicationView:
    """현재 슬롯의 질문을 생성하고 동시에 요청되어도 하나만 저장합니다."""
    with Session(engine) as db:
        row = owned_application(db, application_id, applicant)
        slot = unanswered(db, row)
        if slot is None or db.get(InterviewQuestion, (row.id, slot[0])) is not None:
            return application_view(db, row)
        role, stage = row.role, row.stage
        text = re.sub(
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[이메일 생략]", row.resume[:2500]
        )
        excerpt = re.sub(r"(?<!\w)\+?\d[\d ()-]{7,}\d", "[연락처 생략]", text)
        previous = list(
            db.scalars(
                select(InterviewQuestion.prompt).where(
                    InterviewQuestion.application_id == row.id
                )
            )
        )
    key, _, topic, criteria = slot
    if not excerpt:
        topic = topic.replace("지원서에 나온", "실제 또는 가상의")
    result = generate_question(role, stage, topic, criteria, excerpt, previous)
    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        row = owned_application(db, application_id, applicant, lock=True)
        current = unanswered(db, row)
        if (
            current
            and current[0] == key
            and not db.get(InterviewQuestion, (row.id, key))
        ):
            db.add(
                InterviewQuestion(
                    application_id=row.id,
                    question_id=key,
                    prompt=result.prompt,
                    criteria=json.dumps(result.criteria, ensure_ascii=False),
                )
            )
            db.flush()
        return application_view(db, row)


def history(engine: Engine, applicant: str, application_id: int) -> InterviewHistory:
    """현재 계정이 소유한 면접의 전체 답변과 피드백을 조회합니다."""
    with Session(engine) as db:
        row = owned_application(db, application_id, applicant)
        questions = {
            item.question_id: item.prompt
            for item in db.scalars(
                select(InterviewQuestion).where(
                    InterviewQuestion.application_id == row.id
                )
            )
        }
        legacy = {key: prompt for key, _, prompt, _ in (*TECH_BY_ROLE[row.role], *CULT)}
        answers = [
            InterviewEntry(
                question_id=item.question_id,
                prompt=questions.get(
                    item.question_id, legacy.get(item.question_id, item.question_id)
                ),
                answer=item.answer,
                score=item.score,
                evaluation=Evaluation.model_validate_json(item.evaluation)
                if item.evaluation
                else None,
            )
            for item in db.scalars(
                select(InterviewAnswer)
                .where(InterviewAnswer.application_id == row.id)
                .order_by(InterviewAnswer.id)
            )
        ]
        return InterviewHistory(application=application_view(db, row), answers=answers)


def current_question(
    db: Session,
    application_id: int,
    applicant: str,
    question_id: str,
    *,
    for_update: bool = False,
) -> tuple[Application, InterviewQuestion]:
    """답변 소유권과 아직 응답 가능한 질문인지 확인합니다."""
    row = owned_application(db, application_id, applicant, lock=for_update)
    slot = unanswered(db, row)
    question = db.get(InterviewQuestion, (row.id, question_id))
    if slot is None or slot[0] != question_id or question is None:
        raise HTTPException(409, "현재 질문이 변경됐거나 아직 생성되지 않았습니다.")
    return row, question


def submit_answer(
    engine: Engine, applicant: str, application_id: int, data: Answer
) -> ApplicationView:
    """현재 질문의 응답을 평가하고 해당 전형의 마지막 질문이면 결과를 저장합니다."""
    answer = data.answer.strip()
    if not answer:
        raise HTTPException(422, "답변을 입력해 주세요.")
    with Session(engine) as db:
        row, question = current_question(
            db, application_id, applicant, data.question_id
        )
        stage_questions = questions_for(row)
        index = next(
            index
            for index, item in enumerate(stage_questions)
            if item[0] == data.question_id
        )
        prompt = question.prompt
        criteria = tuple(json.loads(question.criteria))
    evaluation = evaluate(data.question_id, prompt, criteria, answer)

    with Session(engine) as db, db.begin():
        lock_sqlite_write(db)
        row, _ = current_question(
            db, application_id, applicant, data.question_id, for_update=True
        )
        db.add(
            InterviewAnswer(
                application_id=row.id,
                question_id=data.question_id,
                answer=answer,
                score=evaluation.score,
                evaluation=evaluation.model_dump_json(),
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
