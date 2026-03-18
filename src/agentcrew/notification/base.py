"""알림 추상 인터페이스 정의.

Slack, Discord, Email 등 다양한 알림 채널을 추상화한다.

Closes #47
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


class NotificationLevel(enum.Enum):
    """알림 수준."""

    SUCCESS = "success"
    FAILURE = "failure"
    INFO = "info"


@dataclass
class NotificationPayload:
    """알림 페이로드.

    Attributes:
        level: 알림 수준 (success / failure / info).
        title: 알림 제목.
        message: 알림 본문.
        details: 추가 정보 딕셔너리.
    """

    level: NotificationLevel
    title: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class Notifier(ABC):
    """알림 발송 추상 인터페이스.

    모든 알림 채널(Discord, Slack, Email 등)은
    이 인터페이스를 구현해야 한다.
    """

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """알림을 발송한다.

        Args:
            payload: 알림 페이로드.

        Returns:
            발송 성공 여부.
        """
        ...
