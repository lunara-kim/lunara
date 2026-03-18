"""tasks.yaml Pydantic 스키마.

Agent 2가 생성하고 Agent 3/4가 갱신하는 작업 목록 모델 정의.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class TaskLayer(StrEnum):
    """작업 레이어 (아키텍처 계층)."""

    ENTITY = "entity"
    REPOSITORY = "repository"
    SERVICE = "service"
    CONTROLLER = "controller"
    CONFIG = "config"
    TEST = "test"
    INFRA = "infra"


class TaskPriority(StrEnum):
    """작업 우선순위."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(StrEnum):
    """작업 상태."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    QA_PASS = "qa_pass"
    QA_FAIL = "qa_fail"


class Task(BaseModel):
    """개별 작업 항목."""

    id: str = Field(..., description="작업 고유 ID (예: TASK-001)")
    title: str = Field(..., description="작업 제목")
    description: str = Field(default="", description="작업 상세 설명")
    layer: TaskLayer = Field(..., description="아키텍처 레이어")
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="우선순위",
    )
    estimated_hours: float = Field(
        default=1.0,
        gt=0,
        description="예상 소요 시간 (시간 단위)",
    )
    status: TaskStatus = Field(
        default=TaskStatus.NEW,
        description="작업 상태",
    )
    files_changed: list[str] = Field(
        default_factory=list,
        description="변경 대상 파일 경로 목록",
    )
    qa_task_id: Optional[str] = Field(
        default=None,
        description="이 작업에 대응하는 QA 작업 ID",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="선행 작업 ID 목록",
    )


class TasksFile(BaseModel):
    """tasks.yaml 최상위 구조."""

    tasks: list[Task] = Field(default_factory=list, description="작업 목록")
