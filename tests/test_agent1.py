"""Agent 1 유닛테스트."""

from __future__ import annotations

import asyncio
from typing import Optional

import pytest
import yaml

from agentcrew.agents.agent1.agent import RequirementsAgent
from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent1.models import (
    FunctionalRequirement,
    InputType,
    NonFunctionalRequirement,
    PingPongState,
    RequirementsDocument,
    UnresolvedItem,
)
from agentcrew.agents.agent1.parser import (
    detect_input_type,
    extract_key_points,
    extract_speakers,
    parse_input,
)
from agentcrew.agents.agent1.pingpong import collect_unresolved_items, generate_questions, run_pingpong
from agentcrew.agents.agent1.renderer import render_requirements_md


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

MOCK_EXTRACT_RESPONSE = """\
```yaml
summary: "온라인 쇼핑몰 구축"
functional:
  - id: "FR-001"
    title: "사용자 회원가입"
    description: "이메일로 회원가입할 수 있다"
    scenarios:
      - "사용자가 이메일과 비밀번호로 가입한다"
    edge_cases:
      - "이미 가입된 이메일로 가입 시도"
    exceptions:
      - "이메일 형식이 올바르지 않은 경우 오류 메시지 표시"
  - id: "FR-002"
    title: "상품 검색"
    description: "키워드로 상품을 검색할 수 있다"
    scenarios:
      - "사용자가 검색창에 키워드를 입력한다"
    edge_cases:
      - "검색 결과가 없는 경우"
    exceptions:
      - "특수문자만 입력된 경우 안내 메시지"
non_functional:
  - id: "NFR-001"
    category: "성능"
    description: "검색 응답 시간 2초 이내"
    acceptance_criteria: "95% 요청이 2초 이내 응답"
```
"""

MOCK_QUESTIONS_RESPONSE = """\
```yaml
questions:
  - "결제 수단은 어떤 것을 지원하나요?"
  - "회원 등급 시스템이 필요한가요?"
```
"""

MOCK_EMPTY_QUESTIONS = """\
```yaml
questions: []
```
"""


class MockLLM:
    """테스트용 Mock LLM."""

    def __init__(self, responses: Optional[list[str]] = None) -> None:
        self._responses = responses or [MOCK_EXTRACT_RESPONSE]
        self._call_count = 0
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, system: str = "") -> str:
        """Mock 응답 반환."""
        self.prompts.append(prompt)
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]


# ---------------------------------------------------------------------------
# #15: 텍스트 입력 파싱 로직
# ---------------------------------------------------------------------------

class TestParser:
    """파서 테스트."""

    def test_detect_chat_log(self) -> None:
        text = "철수: 로그인 기능 필요해\n영희: 회원가입도 추가하자\n철수: 좋아"
        assert detect_input_type(text) == InputType.CHAT_LOG

    def test_detect_meeting_notes(self) -> None:
        text = "회의록\n일시: 2024-01-01\n참석자: 김철수, 이영희\n안건: 신규 프로젝트"
        assert detect_input_type(text) == InputType.MEETING_NOTES

    def test_detect_free_text(self) -> None:
        text = "온라인 쇼핑몰을 만들고 싶습니다. 상품을 등록하고 판매하는 기능이 필요합니다."
        assert detect_input_type(text) == InputType.FREE_TEXT

    def test_extract_speakers_chat(self) -> None:
        text = "철수: 안녕\n영희: 반가워\n철수: 시작하자"
        speakers = extract_speakers(text, InputType.CHAT_LOG)
        assert speakers == ["철수", "영희"]

    def test_extract_speakers_free_text(self) -> None:
        text = "상품 관리 시스템이 필요합니다."
        speakers = extract_speakers(text, InputType.FREE_TEXT)
        assert speakers == []

    def test_extract_key_points(self) -> None:
        text = "로그인 기능이 필요합니다. 날씨가 좋네요. 검색 기능을 구현해야 합니다."
        points = extract_key_points(text)
        assert len(points) >= 2
        assert any("필요" in p or "구현" in p for p in points)

    def test_parse_input_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="비어"):
            parse_input("")

    def test_parse_input_success(self) -> None:
        text = "철수: 회원가입 기능 필요해\n영희: 좋아, 추가하자"
        result = parse_input(text)
        assert result.input_type == InputType.CHAT_LOG
        assert "철수" in result.speakers
        assert result.raw_text == text


# ---------------------------------------------------------------------------
# #14: 프롬프트 템플릿
# ---------------------------------------------------------------------------

class TestPromptTemplates:
    """프롬프트 템플릿 테스트."""

    def test_templates_importable(self) -> None:
        from agentcrew.agents.agent1.prompts.templates import (
            EXTRACT_REQUIREMENTS_PROMPT,
            GENERATE_QUESTIONS_PROMPT,
            REFINE_REQUIREMENTS_PROMPT,
            REQUIREMENTS_MD_PROMPT,
            SYSTEM_PROMPT,
        )
        assert "{input_text}" in EXTRACT_REQUIREMENTS_PROMPT
        assert "{current_requirements}" in GENERATE_QUESTIONS_PROMPT
        assert "YAML" in SYSTEM_PROMPT

    def test_extract_prompt_format(self) -> None:
        from agentcrew.agents.agent1.prompts.templates import EXTRACT_REQUIREMENTS_PROMPT
        result = EXTRACT_REQUIREMENTS_PROMPT.format(input_text="테스트 입력")
        assert "테스트 입력" in result


# ---------------------------------------------------------------------------
# #16: 핑퐁 질문 로직
# ---------------------------------------------------------------------------

class TestPingPong:
    """핑퐁 로직 테스트."""

    def test_pingpong_state_properties(self) -> None:
        state = PingPongState(max_rounds=3, current_round=1)
        assert state.remaining_rounds == 2

        state.answers_received.append(None)
        assert state.has_unanswered is True

    @pytest.mark.asyncio
    async def test_generate_questions(self) -> None:
        llm = MockLLM([MOCK_QUESTIONS_RESPONSE])
        state = PingPongState()
        questions = await generate_questions(llm, "test yaml", state)
        assert len(questions) == 2
        assert "결제" in questions[0]

    @pytest.mark.asyncio
    async def test_generate_questions_empty(self) -> None:
        llm = MockLLM([MOCK_EMPTY_QUESTIONS])
        state = PingPongState()
        questions = await generate_questions(llm, "test yaml", state)
        assert questions == []

    @pytest.mark.asyncio
    async def test_run_pingpong_no_questions(self) -> None:
        """질문이 없으면 바로 완료."""
        llm = MockLLM([MOCK_EMPTY_QUESTIONS])

        async def ask_user(q: str) -> Optional[str]:
            return "답변입니다"

        state = await run_pingpong(llm, "yaml", ask_user)
        assert state.completed is True
        assert state.current_round == 0

    @pytest.mark.asyncio
    async def test_run_pingpong_with_answers(self) -> None:
        """질문 후 답변을 받는 정상 플로우."""
        llm = MockLLM([MOCK_QUESTIONS_RESPONSE, MOCK_EMPTY_QUESTIONS])

        async def ask_user(q: str) -> Optional[str]:
            return "신용카드와 계좌이체를 지원합니다"

        state = await run_pingpong(llm, "yaml", ask_user)
        assert state.completed is True
        assert state.current_round >= 1
        assert len(state.answers_received) >= 1

    @pytest.mark.asyncio
    async def test_run_pingpong_timeout(self) -> None:
        """타임아웃 테스트."""
        llm = MockLLM([MOCK_QUESTIONS_RESPONSE])

        async def ask_user(q: str) -> Optional[str]:
            await asyncio.sleep(10)
            return "늦은 답변"

        state = await run_pingpong(llm, "yaml", ask_user, timeout_seconds=0)
        assert state.timed_out is True
        assert None in state.answers_received


# ---------------------------------------------------------------------------
# #18: 미결 사항 수집
# ---------------------------------------------------------------------------

class TestUnresolved:
    """미결 사항 수집 테스트."""

    def test_collect_unresolved_timeout(self) -> None:
        state = PingPongState(
            current_round=1,
            questions_asked=["질문1"],
            answers_received=[None],
            timed_out=True,
            completed=True,
        )
        items = collect_unresolved_items(state)
        assert len(items) == 1
        assert "타임아웃" in items[0].reason

    def test_collect_unresolved_max_rounds(self) -> None:
        state = PingPongState(
            max_rounds=3,
            current_round=3,
            questions_asked=["q1", "q2", "q3"],
            answers_received=["a1", "a2", "a3"],
            timed_out=False,
            completed=True,
        )
        items = collect_unresolved_items(state)
        assert len(items) == 1
        assert "초과" in items[0].reason

    def test_collect_unresolved_empty(self) -> None:
        state = PingPongState(
            max_rounds=3,
            current_round=1,
            questions_asked=["q1"],
            answers_received=["a1"],
            completed=True,
        )
        items = collect_unresolved_items(state)
        assert items == []


# ---------------------------------------------------------------------------
# #17: requirements.md 생성
# ---------------------------------------------------------------------------

class TestRenderer:
    """렌더러 테스트."""

    def test_render_full_document(self) -> None:
        doc = RequirementsDocument(
            title="테스트 프로젝트",
            summary="테스트 요약",
            functional=[
                FunctionalRequirement(
                    id="FR-001",
                    title="로그인",
                    description="이메일 로그인",
                    scenarios=["이메일 입력 후 로그인"],
                    edge_cases=["잘못된 비밀번호"],
                    exceptions=["계정 잠금 시 안내"],
                )
            ],
            non_functional=[
                NonFunctionalRequirement(
                    id="NFR-001",
                    category="성능",
                    description="응답 2초 이내",
                    acceptance_criteria="95% 이내",
                )
            ],
            unresolved=[
                UnresolvedItem(
                    id="UR-001",
                    question="결제 수단?",
                    context="핑퐁 라운드 1",
                    reason="타임아웃",
                )
            ],
        )
        md = render_requirements_md(doc)
        assert "# 테스트 프로젝트" in md
        assert "## 기능 요구사항" in md
        assert "FR-001" in md
        assert "## 비기능 요구사항" in md
        assert "NFR-001" in md
        assert "## 미결 사항" in md
        assert "UR-001" in md

    def test_render_empty_document(self) -> None:
        doc = RequirementsDocument(title="빈 문서")
        md = render_requirements_md(doc)
        assert "# 빈 문서" in md
        assert "## 기능 요구사항" not in md


# ---------------------------------------------------------------------------
# Agent 통합 테스트
# ---------------------------------------------------------------------------

class TestRequirementsAgent:
    """RequirementsAgent 통합 테스트."""

    @pytest.mark.asyncio
    async def test_extract_requirements(self) -> None:
        llm = MockLLM([MOCK_EXTRACT_RESPONSE])
        agent = RequirementsAgent(llm)

        doc = await agent.extract_requirements("쇼핑몰을 만들고 싶습니다")
        assert doc.summary == "온라인 쇼핑몰 구축"
        assert len(doc.functional) == 2
        assert doc.functional[0].id == "FR-001"
        assert len(doc.non_functional) == 1

    @pytest.mark.asyncio
    async def test_run_without_pingpong(self) -> None:
        llm = MockLLM([MOCK_EXTRACT_RESPONSE])
        agent = RequirementsAgent(llm)

        doc, md = await agent.run("쇼핑몰을 만들고 싶습니다")
        assert "FR-001" in md
        assert "온라인 쇼핑몰 구축" in md
        assert doc.summary == "온라인 쇼핑몰 구축"

    @pytest.mark.asyncio
    async def test_run_with_pingpong(self) -> None:
        llm = MockLLM([
            MOCK_EXTRACT_RESPONSE,
            MOCK_QUESTIONS_RESPONSE,
            MOCK_EMPTY_QUESTIONS,
        ])
        agent = RequirementsAgent(llm)

        async def ask_user(q: str) -> Optional[str]:
            return "답변입니다"

        doc, md = await agent.run("쇼핑몰을 만들고 싶습니다", ask_user=ask_user)
        assert "FR-001" in md

    @pytest.mark.asyncio
    async def test_llm_protocol(self) -> None:
        """MockLLM이 LLMProvider 프로토콜을 만족하는지 확인."""
        llm = MockLLM()
        assert isinstance(llm, LLMProvider)
