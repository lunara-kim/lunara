"""Agent 1 — 요구사항 구체화 에이전트.

텍스트 입력을 받아 구조화된 RequirementsDocument를 생성하는 메인 에이전트 클래스.
"""

from __future__ import annotations

from typing import Callable, Awaitable, Optional

import yaml

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent1.models import (
    FunctionalRequirement,
    NonFunctionalRequirement,
    RequirementsDocument,
)
from agentcrew.agents.agent1.parser import parse_input
from agentcrew.agents.agent1.pingpong import collect_unresolved_items, run_pingpong
from agentcrew.agents.agent1.prompts.templates import (
    EXTRACT_REQUIREMENTS_PROMPT,
    SYSTEM_PROMPT,
)
from agentcrew.agents.agent1.renderer import render_requirements_md


class RequirementsAgent:
    """요구사항 구체화 에이전트.

    텍스트 입력(회의록/채팅)을 분석하여 구조화된 requirements.md를 생성한다.

    Args:
        llm: LLM 프로바이더 인스턴스.
        timeout_seconds: 핑퐁 타임아웃 (초). 기본 600.
    """

    def __init__(self, llm: LLMProvider, *, timeout_seconds: int = 600) -> None:
        self._llm = llm
        self._timeout_seconds = timeout_seconds

    async def extract_requirements(self, text: str) -> RequirementsDocument:
        """텍스트에서 요구사항을 추출한다.

        Args:
            text: 원본 입력 텍스트.

        Returns:
            추출된 요구사항 문서.

        Raises:
            ValueError: 빈 텍스트 입력 시.
        """
        parsed = parse_input(text)

        prompt = EXTRACT_REQUIREMENTS_PROMPT.format(input_text=parsed.raw_text)
        response = await self._llm.generate(prompt, system=SYSTEM_PROMPT)

        return self._parse_llm_response(response)

    async def run(
        self,
        text: str,
        ask_user: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
    ) -> tuple[RequirementsDocument, str]:
        """전체 요구사항 구체화 파이프라인을 실행한다.

        1. 텍스트 파싱
        2. LLM으로 요구사항 추출
        3. 핑퐁 질문 (ask_user가 제공된 경우)
        4. 미결 사항 추가
        5. requirements.md 생성

        Args:
            text: 원본 입력 텍스트.
            ask_user: 사용자에게 질문하는 콜백 (없으면 핑퐁 생략).

        Returns:
            (RequirementsDocument, requirements.md 문자열) 튜플.
        """
        doc = await self.extract_requirements(text)

        if ask_user is not None:
            requirements_yaml = self._doc_to_yaml(doc)
            state = await run_pingpong(
                self._llm,
                requirements_yaml,
                ask_user,
                timeout_seconds=self._timeout_seconds,
            )
            unresolved = collect_unresolved_items(state)
            doc.unresolved.extend(unresolved)

        md = render_requirements_md(doc)
        return doc, md

    def _parse_llm_response(self, response: str) -> RequirementsDocument:
        """LLM 응답을 RequirementsDocument로 파싱한다.

        Args:
            response: LLM 응답 텍스트 (YAML 포함).

        Returns:
            파싱된 RequirementsDocument.
        """
        try:
            if "```yaml" in response:
                yaml_block = response.split("```yaml")[1].split("```")[0]
            elif "```" in response:
                yaml_block = response.split("```")[1].split("```")[0]
            else:
                yaml_block = response

            data = yaml.safe_load(yaml_block)
        except (yaml.YAMLError, IndexError):
            data = {}

        if not isinstance(data, dict):
            data = {}

        functional = []
        for item in data.get("functional", []):
            if isinstance(item, dict):
                functional.append(FunctionalRequirement(**item))

        non_functional = []
        for item in data.get("non_functional", []):
            if isinstance(item, dict):
                non_functional.append(NonFunctionalRequirement(**item))

        return RequirementsDocument(
            summary=data.get("summary", ""),
            functional=functional,
            non_functional=non_functional,
        )

    @staticmethod
    def _doc_to_yaml(doc: RequirementsDocument) -> str:
        """RequirementsDocument를 YAML 문자열로 변환한다."""
        data = {
            "summary": doc.summary,
            "functional": [fr.model_dump() for fr in doc.functional],
            "non_functional": [nfr.model_dump() for nfr in doc.non_functional],
        }
        return yaml.dump(data, allow_unicode=True, default_flow_style=False)
