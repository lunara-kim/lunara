"""Discord webhook 알림 구현.

Closes #48
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from agentcrew.notification.base import Notifier, NotificationLevel, NotificationPayload

logger = logging.getLogger(__name__)

# Discord embed 색상
_COLORS = {
    NotificationLevel.SUCCESS: 0x2ECC71,  # 녹색
    NotificationLevel.FAILURE: 0xE74C3C,  # 빨간색
    NotificationLevel.INFO: 0x3498DB,     # 파란색
}

_EMOJIS = {
    NotificationLevel.SUCCESS: "✅",
    NotificationLevel.FAILURE: "❌",
    NotificationLevel.INFO: "ℹ️",
}


class DiscordNotifier(Notifier):
    """Discord webhook을 통한 알림 발송.

    외부 의존성 없이 urllib만 사용한다.

    Args:
        webhook_url: Discord webhook URL.
        timeout: HTTP 요청 타임아웃 (초).
    """

    def __init__(self, webhook_url: str, *, timeout: int = 10) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def send(self, payload: NotificationPayload) -> bool:
        """Discord webhook으로 알림을 발송한다."""
        embed = self._build_embed(payload)
        body = json.dumps({"embeds": [embed]}).encode("utf-8")

        req = Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                logger.info("Discord 알림 발송 성공: %s", resp.status)
                return True
        except (URLError, HTTPError) as e:
            logger.error("Discord 알림 발송 실패: %s", e)
            return False

    @staticmethod
    def _build_embed(payload: NotificationPayload) -> dict:
        """Discord embed 객체를 생성한다."""
        emoji = _EMOJIS.get(payload.level, "")
        embed: dict = {
            "title": f"{emoji} {payload.title}",
            "description": payload.message,
            "color": _COLORS.get(payload.level, 0x95A5A6),
        }

        if payload.details:
            fields = []
            for k, v in payload.details.items():
                fields.append({"name": k, "value": str(v), "inline": True})
            embed["fields"] = fields

        return embed
