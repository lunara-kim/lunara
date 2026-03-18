"""progress.json Pydantic 스키마.

파이프라인 실행 상태를 추적하기 위한 모델 정의.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class PipelineStatus(StrEnum):
    """파이프라인 실행 상태."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ProgressError(BaseModel):
    """파이프라인 오류 정보."""

    agent: str = Field(..., description="오류가 발생한 에이전트 이름")
    message: str = Field(..., description="오류 메시지")
    timestamp: datetime = Field(..., description="오류 발생 시각")
    retry_count: int = Field(default=0, ge=0, description="재시도 횟수")


class Progress(BaseModel):
    """파이프라인 실행 상태 (progress.json)."""

    pipeline_status: PipelineStatus = Field(
        default=PipelineStatus.IDLE,
        description="파이프라인 실행 상태",
    )
    current_agent: Optional[str] = Field(
        default=None,
        description="현재 실행 중인 에이전트 이름 (예: agent1, agent2, agent3, agent4)",
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="파이프라인 시작 시각",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="마지막 상태 갱신 시각",
    )
    error: Optional[ProgressError] = Field(
        default=None,
        description="최근 오류 정보 (없으면 null)",
    )
