"""파이프라인 실패 시 중단 + 로그 저장 로직.

Closes #44
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineLog:
    """파이프라인 실행 로그 엔트리."""

    timestamp: str
    agent: str
    level: str
    message: str
    detail: Optional[str] = None


@dataclass
class FailureHandler:
    """파이프라인 실패를 처리하고 로그를 저장한다.

    Args:
        log_dir: 로그 저장 디렉토리.
    """

    log_dir: str | Path = "pipeline-logs"
    _logs: list[PipelineLog] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.log_dir = Path(self.log_dir)

    def add_log(
        self,
        agent: str,
        level: str,
        message: str,
        *,
        detail: Optional[str] = None,
    ) -> None:
        """로그 엔트리를 추가한다."""
        entry = PipelineLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent,
            level=level,
            message=message,
            detail=detail,
        )
        self._logs.append(entry)
        log_fn = logger.error if level == "ERROR" else logger.info
        log_fn("[%s] %s: %s", agent, level, message)

    def save_logs(self, *, suffix: str = "") -> Path:
        """수집된 로그를 JSON 파일로 저장한다.

        Returns:
            저장된 로그 파일 경로.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = f"pipeline_{ts}{suffix}.json"
        path = self.log_dir / name

        data = [
            {
                "timestamp": log.timestamp,
                "agent": log.agent,
                "level": log.level,
                "message": log.message,
                "detail": log.detail,
            }
            for log in self._logs
        ]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("파이프라인 로그 저장: %s", path)
        return path

    @property
    def logs(self) -> list[PipelineLog]:
        """현재까지 수집된 로그를 반환한다."""
        return list(self._logs)

    def has_errors(self) -> bool:
        """에러 로그가 있는지 확인한다."""
        return any(log.level == "ERROR" for log in self._logs)


class PipelineAbortError(Exception):
    """파이프라인 중단 예외.

    Attributes:
        agent: 실패한 에이전트 이름.
        reason: 실패 사유.
        log_path: 저장된 로그 파일 경로.
    """

    def __init__(
        self,
        agent: str,
        reason: str,
        log_path: Optional[Path] = None,
    ) -> None:
        self.agent = agent
        self.reason = reason
        self.log_path = log_path
        super().__init__(f"Pipeline aborted at {agent}: {reason}")
