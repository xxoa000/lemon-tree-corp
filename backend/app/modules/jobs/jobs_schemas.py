"""채용 공고, 지원 건, 모의면접 요청과 응답을 정의합니다."""

from pydantic import BaseModel, ConfigDict, Field


class Posting(BaseModel):
    """현재 채용 공고와 업무 내용을 표시합니다."""

    role: str
    criteria: str
    title: str
    team: str
    duties: list[str]
    format: str


class Question(BaseModel):
    """면접관이 제시하는 한 질문을 표시합니다."""

    id: str
    interviewer: str
    prompt: str


class Answer(BaseModel):
    """현재 질문에 대한 답변을 받습니다."""

    question_id: str = Field(max_length=30)
    answer: str = Field(min_length=1, max_length=3000)


class CriterionAssessment(BaseModel):
    """평가 항목 한 개의 충족 여부와 인용 근거입니다."""

    model_config = ConfigDict(extra="forbid", strict=True)
    met: bool
    evidence: str = Field(max_length=180)


class Correction(BaseModel):
    """원문의 잘못된 설명과 보완할 내용을 담습니다."""

    model_config = ConfigDict(extra="forbid", strict=True)
    quote: str = Field(min_length=1, max_length=180)
    correction: str = Field(min_length=1, max_length=240)


class GeneratedQuestion(BaseModel):
    """면접 질문과 답변 전에 확정할 채점 기준입니다."""

    model_config = ConfigDict(extra="forbid", strict=True)
    prompt: str = Field(min_length=10, max_length=700)
    criteria: list[str] = Field(min_length=3, max_length=3)


class Assessment(BaseModel):
    """Ollama가 구조화된 JSON으로 반환하는 평가 결과입니다."""

    model_config = ConfigDict(extra="forbid", strict=True)
    criteria: list[CriterionAssessment] = Field(min_length=3, max_length=3)
    feedback: str = Field(min_length=1, max_length=300)
    corrections: list[Correction] = Field(max_length=4)
    model_answer: str = Field(min_length=1, max_length=1200)


class Evaluation(Assessment):
    """지원자가 다시 볼 수 있도록 평가 기준과 점수를 함께 보관합니다."""

    question_id: str
    score: int
    labels: list[str]
    corrections: list[Correction] = Field(default_factory=list, max_length=4)
    model_answer: str = Field(default="", max_length=1200)


class ApplicationView(BaseModel):
    """지원 건과 이어서 답변할 다음 질문을 표시합니다."""

    id: int
    role: str
    filename: str
    stage: str
    feedback: str
    created_at: str
    question: Question | None
    latest_evaluation: Evaluation | None = None
    latest_answer: str | None = None


class InterviewEntry(BaseModel):
    """한 질문의 원문, 답변과 당시 평가를 소유자에게 표시합니다."""

    question_id: str
    prompt: str
    answer: str
    score: int
    evaluation: Evaluation | None


class InterviewHistory(BaseModel):
    """지원 건의 진행 상태와 답변 내역입니다."""

    application: ApplicationView
    answers: list[InterviewEntry]
