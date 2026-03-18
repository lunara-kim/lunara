"""Selective Context 주입 로직.

Agent별 필요한 파일만 선택적으로 전달한다.

Closes #45
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Agent별 기본 컨텍스트 파일 매핑
DEFAULT_CONTEXT_MAP: dict[str, list[str]] = {
    "agent1": [
        # Agent 1: 요구사항 구체화 — 원본 입력만 필요
    ],
    "agent2": [
        # Agent 2: 작업 목록 생성 — requirements.md 필요
        "requirements.md",
    ],
    "agent3": [
        # Agent 3: 코드 구현 — tasks.yaml + 기존 소스코드
        "tasks.yaml",
        "progress.json",
    ],
    "agent4": [
        # Agent 4: QA 검증 — tasks.yaml + 구현된 코드
        "tasks.yaml",
    ],
}


@dataclass
class ContextInjector:
    """Agent별 필요한 컨텍스트를 선택적으로 주입한다.

    Args:
        project_root: 프로젝트 루트 디렉토리.
        context_map: Agent별 필요 파일 매핑 (커스터마이징 가능).
    """

    project_root: str | Path
    context_map: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_CONTEXT_MAP))

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root)

    def get_context_files(self, agent_name: str) -> list[str]:
        """특정 Agent에 필요한 컨텍스트 파일 경로 목록을 반환한다.

        Args:
            agent_name: 에이전트 이름 (예: "agent1").

        Returns:
            파일 경로 리스트.
        """
        return list(self.context_map.get(agent_name, []))

    def load_context(
        self,
        agent_name: str,
        *,
        extra_files: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """Agent에 필요한 파일들을 읽어 딕셔너리로 반환한다.

        Args:
            agent_name: 에이전트 이름.
            extra_files: 추가로 주입할 파일 경로 목록.

        Returns:
            {파일 경로: 파일 내용} 딕셔너리.
        """
        files = self.get_context_files(agent_name)
        if extra_files:
            files = files + extra_files

        context: dict[str, str] = {}
        for file_path in files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    context[file_path] = content
                    logger.debug("컨텍스트 로드: %s (%d bytes)", file_path, len(content))
                except Exception as e:
                    logger.warning("컨텍스트 로드 실패: %s — %s", file_path, e)
            else:
                logger.debug("컨텍스트 파일 없음 (건너뜀): %s", file_path)

        return context

    def format_context(self, context: dict[str, str]) -> str:
        """컨텍스트 딕셔너리를 프롬프트에 삽입 가능한 문자열로 포맷한다.

        Args:
            context: {파일 경로: 파일 내용} 딕셔너리.

        Returns:
            포맷된 컨텍스트 문자열.
        """
        if not context:
            return ""

        parts: list[str] = []
        for path, content in context.items():
            parts.append(f"--- {path} ---")
            parts.append(content)
            parts.append("")

        return "\n".join(parts)

    def add_context_file(self, agent_name: str, file_path: str) -> None:
        """Agent의 컨텍스트 파일 목록에 파일을 추가한다."""
        if agent_name not in self.context_map:
            self.context_map[agent_name] = []
        if file_path not in self.context_map[agent_name]:
            self.context_map[agent_name].append(file_path)
