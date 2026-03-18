"""파이프라인 완료/실패 시 알림 발송 로직.

Closes #49
"""

from __future__ import annotations

import logging
from typing import Optional

from agentcrew.notification.base import Notifier, NotificationLevel, NotificationPayload
from agentcrew.schemas.config import NotificationConfig, NotificationType
from agentcrew.notification.discord import DiscordNotifier

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """파이프라인 이벤트에 따라 알림을 발송하는 디스패처.

    Args:
        config: NotificationConfig 설정 객체.
    """

    def __init__(self, config: NotificationConfig) -> None:
        self.config = config
        self._notifier: Optional[Notifier] = None

        if config.enabled:
            self._notifier = self._create_notifier(config)

    @staticmethod
    def _create_notifier(config: NotificationConfig) -> Optional[Notifier]:
        """설정에 따라 적절한 Notifier를 생성한다."""
        if config.type == NotificationType.DISCORD:
            if not config.webhook_url:
                logger.warning("Discord webhook URL이 설정되지 않음. 알림 비활성화.")
                return None
            return DiscordNotifier(config.webhook_url)
        # Slack, Email은 추후 구현
        logger.warning("지원하지 않는 알림 타입: %s", config.type)
        return None

    async def notify_success(self, *, details: Optional[dict] = None) -> bool:
        """파이프라인 성공 알림을 발송한다."""
        if not self._notifier:
            return False

        payload = NotificationPayload(
            level=NotificationLevel.SUCCESS,
            title="파이프라인 완료",
            message="모든 에이전트가 성공적으로 실행을 완료했습니다.",
            details=details or {},
        )
        return await self._notifier.send(payload)

    async def notify_failure(
        self,
        *,
        agent: str = "unknown",
        reason: str = "",
        details: Optional[dict] = None,
    ) -> bool:
        """파이프라인 실패 알림을 발송한다."""
        if not self._notifier:
            return False

        d = {"실패 에이전트": agent, "원인": reason}
        if details:
            d.update(details)

        payload = NotificationPayload(
            level=NotificationLevel.FAILURE,
            title="파이프라인 실패",
            message=f"에이전트 '{agent}'에서 오류가 발생했습니다.",
            details=d,
        )
        return await self._notifier.send(payload)
