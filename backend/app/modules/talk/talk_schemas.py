"""채팅방, 메시지와 읽음 요청의 전달 형식을 정의합니다."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Dm(BaseModel):
    """연락처에서 선택한 계정입니다."""

    contact: int


class Group(BaseModel):
    """새로 만들 팀별 채팅방의 이름과 팀입니다."""

    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    team: Literal["디자인팀", "개발팀", "인프라팀"]


class Send(BaseModel):
    """전송할 텍스트 메시지입니다."""

    model_config = ConfigDict(str_strip_whitespace=True)
    body: str = Field(min_length=1, max_length=3000)


class Read(BaseModel):
    """실제로 화면에 표시한 마지막 메시지입니다."""

    message_id: int = Field(gt=0)
