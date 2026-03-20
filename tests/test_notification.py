"""알림 모듈 유닛테스트.

Closes #50
"""

from __future__ import annotations

import json
import asyncio
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

from agentcrew.notification.base import (
    Notifier,
    NotificationLevel,
    NotificationPayload,
)
from agentcrew.notification.discord import DiscordNotifier
from agentcrew.notification.dispatcher import NotificationDispatcher
from agentcrew.schemas.config import NotificationConfig, NotificationType


# === base 테스트 ===


class DummyNotifier(Notifier):
    """테스트용 Notifier 구현."""

    def __init__(self):
        self.sent: list[NotificationPayload] = []

    async def send(self, payload: NotificationPayload) -> bool:
        self.sent.append(payload)
        return True


def test_notification_payload_defaults():
    p = NotificationPayload(
        level=NotificationLevel.SUCCESS,
        title="test",
        message="msg",
    )
    assert p.details == {}
    assert p.level == NotificationLevel.SUCCESS


def test_dummy_notifier():
    n = DummyNotifier()
    payload = NotificationPayload(
        level=NotificationLevel.INFO, title="t", message="m"
    )
    result = asyncio.run(n.send(payload))
    assert result is True
    assert len(n.sent) == 1


# === Discord 테스트 ===


class TestDiscordNotifier:
    def test_build_embed_success(self):
        payload = NotificationPayload(
            level=NotificationLevel.SUCCESS,
            title="파이프라인 완료",
            message="성공",
            details={"에이전트": "agent1"},
        )
        embed = DiscordNotifier._build_embed(payload)
        assert "✅" in embed["title"]
        assert embed["color"] == 0x2ECC71
        assert len(embed["fields"]) == 1

    def test_build_embed_failure(self):
        payload = NotificationPayload(
            level=NotificationLevel.FAILURE,
            title="실패",
            message="에러",
        )
        embed = DiscordNotifier._build_embed(payload)
        assert "❌" in embed["title"]
        assert embed["color"] == 0xE74C3C
        assert "fields" not in embed

    @patch("agentcrew.notification.discord.urlopen")
    def test_send_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        notifier = DiscordNotifier("https://discord.com/api/webhooks/test")
        payload = NotificationPayload(
            level=NotificationLevel.SUCCESS, title="ok", message="done"
        )
        result = asyncio.run(notifier.send(payload))
        assert result is True
        mock_urlopen.assert_called_once()

        # 전송된 데이터 검증
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert "embeds" in body

    @patch("agentcrew.notification.discord.urlopen", side_effect=URLError("fail"))
    def test_send_failure(self, mock_urlopen):
        notifier = DiscordNotifier("https://discord.com/api/webhooks/test")
        payload = NotificationPayload(
            level=NotificationLevel.FAILURE, title="err", message="bad"
        )
        result = asyncio.run(notifier.send(payload))
        assert result is False


# === Dispatcher 테스트 ===


class TestNotificationDispatcher:
    def test_disabled_config(self):
        config = NotificationConfig(enabled=False)
        dispatcher = NotificationDispatcher(config)
        assert dispatcher._notifier is None

        result = asyncio.run(dispatcher.notify_success())
        assert result is False

    def test_enabled_without_webhook(self):
        config = NotificationConfig(
            enabled=True, type=NotificationType.DISCORD, webhook_url=None
        )
        dispatcher = NotificationDispatcher(config)
        assert dispatcher._notifier is None

    @patch("agentcrew.notification.discord.urlopen")
    def test_notify_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        config = NotificationConfig(
            enabled=True,
            type=NotificationType.DISCORD,
            webhook_url="https://discord.com/api/webhooks/test",
        )
        dispatcher = NotificationDispatcher(config)
        result = asyncio.run(
            dispatcher.notify_success(details={"duration": "30s"})
        )
        assert result is True

    @patch("agentcrew.notification.discord.urlopen")
    def test_notify_failure(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        config = NotificationConfig(
            enabled=True,
            type=NotificationType.DISCORD,
            webhook_url="https://discord.com/api/webhooks/test",
        )
        dispatcher = NotificationDispatcher(config)
        result = asyncio.run(
            dispatcher.notify_failure(agent="agent3", reason="빌드 실패")
        )
        assert result is True

        # embed 내용 검증
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        embed = body["embeds"][0]
        assert "agent3" in embed["description"]

    def test_unsupported_type(self):
        config = NotificationConfig(
            enabled=True,
            type=NotificationType.SLACK,
            webhook_url="https://hooks.slack.com/test",
        )
        dispatcher = NotificationDispatcher(config)
        assert dispatcher._notifier is None
