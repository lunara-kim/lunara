"""progress.json 폴링 + 상태 감지 로직.

Closes #43
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agentcrew.schemas.progress import PipelineStatus, Progress, ProgressError

logger = logging.getLogger(__name__)


class ProgressMonitor:
    """progress.json 상태를 관리하고 폴링한다.

    Args:
        progress_path: progress.json 파일 경로.
        poll_interval: 폴링 간격 (초).
    """

    def __init__(
        self,
        progress_path: str | Path,
        *,
        poll_interval: float = 2.0,
    ) -> None:
        self.progress_path = Path(progress_path)
        self.poll_interval = poll_interval

    def load(self) -> Progress:
        """progress.json을 읽어 Progress 객체로 반환한다."""
        if not self.progress_path.exists():
            return Progress()
        text = self.progress_path.read_text(encoding="utf-8")
        data = json.loads(text)
        return Progress.model_validate(data)

    def save(self, progress: Progress) -> None:
        """Progress 객체를 progress.json에 저장한다."""
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        text = progress.model_dump_json(indent=2)
        self.progress_path.write_text(text, encoding="utf-8")

    def update_agent_start(self, agent_name: str) -> Progress:
        """에이전트 실행 시작을 기록한다."""
        progress = self.load()
        now = datetime.now(timezone.utc)
        progress.pipeline_status = PipelineStatus.RUNNING
        progress.current_agent = agent_name
        progress.updated_at = now
        if progress.started_at is None:
            progress.started_at = now
        self.save(progress)
        logger.info("에이전트 시작: %s", agent_name)
        return progress

    def update_agent_done(self, agent_name: str) -> Progress:
        """에이전트 실행 완료를 기록한다."""
        progress = self.load()
        progress.updated_at = datetime.now(timezone.utc)
        self.save(progress)
        logger.info("에이전트 완료: %s", agent_name)
        return progress

    def mark_success(self) -> Progress:
        """파이프라인 성공을 기록한다."""
        progress = self.load()
        progress.pipeline_status = PipelineStatus.SUCCESS
        progress.current_agent = None
        progress.updated_at = datetime.now(timezone.utc)
        self.save(progress)
        return progress

    def mark_failed(self, agent_name: str, message: str) -> Progress:
        """파이프라인 실패를 기록한다."""
        progress = self.load()
        now = datetime.now(timezone.utc)
        progress.pipeline_status = PipelineStatus.FAILED
        progress.current_agent = None
        progress.updated_at = now
        progress.error = ProgressError(
            agent=agent_name,
            message=message,
            timestamp=now,
        )
        self.save(progress)
        logger.error("파이프라인 실패: agent=%s, message=%s", agent_name, message)
        return progress

    async def poll_until_complete(
        self,
        *,
        timeout: float = 600.0,
    ) -> Progress:
        """progress.json을 폴링하여 완료/실패까지 대기한다.

        Args:
            timeout: 최대 대기 시간 (초).

        Returns:
            최종 Progress 상태.

        Raises:
            TimeoutError: 타임아웃 초과 시.
        """
        elapsed = 0.0
        while elapsed < timeout:
            progress = self.load()
            if progress.pipeline_status in (
                PipelineStatus.SUCCESS,
                PipelineStatus.FAILED,
            ):
                return progress
            await asyncio.sleep(self.poll_interval)
            elapsed += self.poll_interval

        raise TimeoutError(
            f"progress.json 폴링 타임아웃 ({timeout}초)"
        )
