"""Agent 1 도메인 모델.

요구사항 구체화 과정에서 사용되는 데이터 모델 정의.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class InputType(StrEnum):
    """입력 텍스트 유형."""

    MEETING_NOTES = "meeting_notes"
    CHAT_LOG = "chat_log"
    FREE_TEXT = "free_text"


class ParsedInput(BaseModel):
    """파싱된 입력 텍스트."""

    raw_text: str = Field(..., description="원본 텍스트")
    input_type: InputType = Field(default=InputType.FREE_TEXT, description="입력 유형")
    speakers: list[str] = Field(default_factory=list, description="발화자 목록")
    key_points: list[str] = Field(default_factory=list, description="핵심 포인트")
    parsed_at: datetime = Field(default_factory=datetime.now, description="파싱 시각")


class FunctionalRequirement(BaseModel):
    """기능 요구사항."""

    id: str = Field(..., description="요구사항 ID (예: FR-001)")
    title: str = Field(..., description="요구사항 제목")
    description: str = Field(default="", description="상세 설명")
    scenarios: list[str] = Field(default_factory=list, description="사용 시나리오")
    edge_cases: list[str] = Field(default_factory=list, description="엣지 케이스")
    exceptions: list[str] = Field(default_factory=list, description="예외 처리 사항")


class NonFunctionalRequirement(BaseModel):
    """비기능 요구사항."""

    id: str = Field(..., description="요구사항 ID (예: NFR-001)")
    category: str = Field(..., description="카테고리 (성능, 보안, 확장성 등)")
    description: str = Field(..., description="상세 설명")
    acceptance_criteria: str = Field(default="", description="수용 기준")


class UnresolvedItem(BaseModel):
    """미결 사항."""

    id: str = Field(..., description="미결 사항 ID (예: UR-001)")
    question: str = Field(..., description="미해결 질문")
    context: str = Field(default="", description="관련 맥락")
    reason: str = Field(default="", description="미결 사유 (타임아웃, 질문 횟수 초과 등)")


class RequirementsDocument(BaseModel):
    """최종 요구사항 문서 모델."""

    title: str = Field(default="Requirements", description="문서 제목")
    summary: str = Field(default="", description="프로젝트 요약")
    functional: list[FunctionalRequirement] = Field(
        default_factory=list, description="기능 요구사항 목록"
    )
    non_functional: list[NonFunctionalRequirement] = Field(
        default_factory=list, description="비기능 요구사항 목록"
    )
    unresolved: list[UnresolvedItem] = Field(
        default_factory=list, description="미결 사항 목록"
    )


class PingPongState(BaseModel):
    """핑퐁 질문 상태 추적."""

    max_rounds: int = Field(default=3, description="최대 질문 라운드")
    current_round: int = Field(default=0, description="현재 라운드")
    timeout_minutes: int = Field(default=10, description="무응답 타임아웃 (분)")
    questions_asked: list[str] = Field(default_factory=list, description="지금까지 한 질문들")
    answers_received: list[Optional[str]] = Field(
        default_factory=list, description="받은 답변 (타임아웃 시 None)"
    )
    timed_out: bool = Field(default=False, description="타임아웃 발생 여부")
    completed: bool = Field(default=False, description="핑퐁 완료 여부")

    @property
    def remaining_rounds(self) -> int:
        """남은 질문 라운드 수."""
        return max(0, self.max_rounds - self.current_round)

    @property
    def has_unanswered(self) -> bool:
        """미답변 질문 존재 여부."""
        return None in self.answers_received
