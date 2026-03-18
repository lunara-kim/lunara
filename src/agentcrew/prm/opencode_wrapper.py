"""OpenCode CLI 프로그래밍 호출 래퍼.

subprocess로 OpenCode CLI를 호출하고, --model 플래그로 모델별 분리를 지원한다.

Closes #42
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OpenCodeResult:
    """OpenCode CLI 실행 결과."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


@dataclass
class OpenCodeWrapper:
    """OpenCode CLI subprocess 래퍼.

    Args:
        binary: opencode 바이너리 경로.
        default_model: 기본 모델명.
        working_dir: 작업 디렉토리.
        timeout_seconds: 실행 타임아웃 (초).
        env: 추가 환경 변수.
    """

    binary: str = "opencode"
    default_model: str = "gpt-4o"
    working_dir: Optional[str] = None
    timeout_seconds: int = 600
    env: dict[str, str] = field(default_factory=dict)

    def _build_command(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """CLI 명령어를 조립한다."""
        cmd = [self.binary]
        cmd.extend(["--model", model or self.default_model])
        if extra_args:
            cmd.extend(extra_args)
        cmd.extend(["--prompt", prompt])
        return cmd

    async def run(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
    ) -> OpenCodeResult:
        """OpenCode CLI를 비동기로 실행한다.

        Args:
            prompt: LLM에 전달할 프롬프트.
            model: 모델명 (None이면 default_model 사용).
            extra_args: 추가 CLI 인자.

        Returns:
            OpenCodeResult 실행 결과.
        """
        cmd = self._build_command(prompt, model=model, extra_args=extra_args)
        logger.info("OpenCode 실행: %s", " ".join(cmd))

        import os

        env = {**os.environ, **self.env}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
                env=env,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout_seconds,
            )
            result = OpenCodeResult(
                returncode=proc.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            logger.error("OpenCode 타임아웃 (%d초)", self.timeout_seconds)
            if proc:  # type: ignore[possibly-undefined]
                proc.kill()
            result = OpenCodeResult(
                returncode=-1,
                stdout="",
                stderr=f"Timeout after {self.timeout_seconds}s",
            )
        except FileNotFoundError:
            logger.error("OpenCode 바이너리를 찾을 수 없음: %s", self.binary)
            result = OpenCodeResult(
                returncode=-1,
                stdout="",
                stderr=f"Binary not found: {self.binary}",
            )

        logger.info("OpenCode 종료: returncode=%d", result.returncode)
        return result
