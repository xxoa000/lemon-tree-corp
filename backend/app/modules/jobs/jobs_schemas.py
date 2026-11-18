"""채용 공고, 지원 건, 모의면접 요청과 응답을 정의합니다."""

from pydantic import BaseModel, Field


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


class ApplicationView(BaseModel):
    """지원 건과 이어서 답변할 다음 질문을 표시합니다."""

    id: int
    role: str
    filename: str
    stage: str
    feedback: str
    created_at: str
    question: Question | None
