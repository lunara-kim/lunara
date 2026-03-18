"""Agent 2 — 작업 목록 생성 에이전트.

requirements.md를 분석하여 tasks.yaml을 생성하고 사람의 검수를 받는 메인 에이전트 클래스.
"""

from __future__ import annotations

from typing import Optional

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent2.cli import review_tasks_cli
from agentcrew.agents.agent2.generator import (
    generate_tasks,
    render_tasks_yaml,
)
from agentcrew.agents.agent2.parser import parse_requirements_md
from agentcrew.schemas.task import TasksFile


class TaskGenerationAgent:
    """작업 목록 생성 에이전트.

    requirements.md를 읽어 LLM으로 구현 작업을 분해하고,
    사람의 검수를 거쳐 최종 tasks.yaml을 생성한다.

    Args:
        llm: LLM 프로바이더 인스턴스.
        max_retries: 거부 시 재생성 최대 횟수. 기본 3.
    """

    def __init__(self, llm: LLMProvider, *, max_retries: int = 3) -> None:
        self._llm = llm
        self._max_retries = max_retries

    async def run(
        self,
        requirements_md: str,
        *,
        review_fn: Optional[object] = None,
    ) -> tuple[TasksFile, str]:
        """전체 작업 목록 생성 파이프라인을 실행한다.

        1. requirements.md 파싱 (구조 검증)
        2. LLM으로 Task 분해
        3. qa_task_id 자동 부여
        4. 사람 검수 (review_fn 제공 시)
        5. tasks.yaml 생성

        Args:
            requirements_md: requirements.md 파일 내용.
            review_fn: 검수 함수. (yaml_str) -> bool. None이면 자동 승인.

        Returns:
            (TasksFile, tasks.yaml 문자열) 튜플.

        Raises:
            ValueError: requirements_md가 비어 있는 경우.
            RuntimeError: 최대 재시도 초과 시.
        """
        # 구조 검증
        parse_requirements_md(requirements_md)

        actual_review = review_fn if review_fn is not None else lambda _: True

        for attempt in range(1, self._max_retries + 1):
            tasks_file = await generate_tasks(self._llm, requirements_md)
            yaml_str = render_tasks_yaml(tasks_file)

            if actual_review(yaml_str):
                return tasks_file, yaml_str

            if attempt >= self._max_retries:
                raise RuntimeError(
                    f"작업 목록이 {self._max_retries}회 거부되어 생성을 중단합니다."
                )

        # unreachable but satisfies type checker
        raise RuntimeError("예상치 못한 루프 종료")  # pragma: no cover

    async def run_with_cli(self, requirements_md: str) -> tuple[TasksFile, str]:
        """CLI 검수를 포함한 파이프라인을 실행한다.

        Args:
            requirements_md: requirements.md 파일 내용.

        Returns:
            (TasksFile, tasks.yaml 문자열) 튜플.
        """
        return await self.run(requirements_md, review_fn=review_tasks_cli)
