"""내 이력서 조회 및 수정 요청의 구조를 정의합니다."""

from pydantic import BaseModel, ConfigDict, Field


class ResumeSections(BaseModel):
    """이력서 양식에 저장할 공개 범위가 없는 개인 기록입니다."""

    model_config = ConfigDict(str_strip_whitespace=True)
    address: str = Field(default="", max_length=240)
    website: str = Field(default="", max_length=240)
    education: str = Field(default="", max_length=2000)
    experience: str = Field(default="", max_length=6000)
    certificates: str = Field(default="", max_length=2000)
    awards: str = Field(default="", max_length=2000)
    skills: str = Field(default="", max_length=2000)


class ResumeEdit(BaseModel):
    """원본에서 추출한 텍스트와 양식 항목을 갱신합니다."""

    content: str = Field(default="", max_length=24000)
    sections: ResumeSections | None = None


class ResumeView(ResumeEdit):
    """원본 이름과 현재 편집본을 반환합니다."""

    filename: str
