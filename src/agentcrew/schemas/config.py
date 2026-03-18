"""config.yaml Pydantic 스키마.

프로젝트 설정, 에이전트별 설정, 모델 설정, 알림 설정 등을 정의.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class NotificationType(StrEnum):
    """알림 채널 타입."""

    DISCORD = "discord"
    SLACK = "slack"
    EMAIL = "email"


class RepoConfig(BaseModel):
    """대상 레포지토리 설정."""

    url: str = Field(..., description="Git 레포지토리 URL")
    branch: str = Field(default="main", description="기본 브랜치")
    language: str = Field(default="java", description="주 언어")


class StackConfig(BaseModel):
    """기술 스택 설정."""

    framework: str = Field(default="spring-boot", description="프레임워크")
    build_tool: str = Field(default="gradle", description="빌드 도구")
    java_version: Optional[str] = Field(default=None, description="Java 버전")


class ModelConfig(BaseModel):
    """LLM 모델 설정."""

    provider: str = Field(default="openai", description="모델 제공자")
    model: str = Field(default="gpt-4o", description="모델 이름")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(default=4096, gt=0, description="최대 토큰 수")


class AgentConfig(BaseModel):
    """개별 에이전트 설정."""

    enabled: bool = Field(default=True, description="에이전트 활성화 여부")
    model: Optional[ModelConfig] = Field(
        default=None,
        description="에이전트별 모델 설정 (미지정 시 기본 모델 사용)",
    )
    max_retries: int = Field(default=3, ge=1, description="최대 재시도 횟수")
    timeout_minutes: int = Field(default=10, ge=1, description="타임아웃 (분)")


class NotificationConfig(BaseModel):
    """알림 설정."""

    enabled: bool = Field(default=False, description="알림 활성화 여부")
    type: NotificationType = Field(
        default=NotificationType.DISCORD,
        description="알림 채널 타입",
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL (Discord/Slack)",
    )


class AgentsConfig(BaseModel):
    """에이전트별 설정 모음."""

    agent1: AgentConfig = Field(default_factory=AgentConfig, description="Agent 1 (요구사항 구체화)")
    agent2: AgentConfig = Field(default_factory=AgentConfig, description="Agent 2 (작업 목록 생성)")
    agent3: AgentConfig = Field(default_factory=AgentConfig, description="Agent 3 (코드 구현)")
    agent4: AgentConfig = Field(default_factory=AgentConfig, description="Agent 4 (QA 검증)")


class Config(BaseModel):
    """AgentCrew 프로젝트 설정 (config.yaml)."""

    repo: RepoConfig = Field(..., description="대상 레포지토리 설정")
    stack: StackConfig = Field(default_factory=StackConfig, description="기술 스택 설정")
    default_model: ModelConfig = Field(
        default_factory=ModelConfig,
        description="기본 LLM 모델 설정",
    )
    agents: AgentsConfig = Field(default_factory=AgentsConfig, description="에이전트별 설정")
    notification: NotificationConfig = Field(
        default_factory=NotificationConfig,
        description="알림 설정",
    )
