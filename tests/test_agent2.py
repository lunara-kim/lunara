"""Agent 2 유닛테스트."""

from __future__ import annotations

import asyncio
from io import StringIO
from typing import Optional
from unittest.mock import patch

import pytest
import yaml

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent2.agent import TaskGenerationAgent
from agentcrew.agents.agent2.cli import review_tasks_cli
from agentcrew.agents.agent2.generator import (
    _parse_tasks_response,
    assign_qa_task_ids,
    generate_tasks,
    render_tasks_yaml,
)
from agentcrew.agents.agent2.parser import (
    ParsedRequirements,
    RequirementSection,
    parse_requirements_md,
)
from agentcrew.schemas.task import Task, TaskLayer, TaskPriority, TasksFile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_REQUIREMENTS_MD = """\
# Requirements

## 프로젝트 요약

온라인 쇼핑몰 구축 프로젝트

## 기능 요구사항

### FR-001: 사용자 회원가입
- **설명:** 이메일로 회원가입할 수 있다
- **시나리오:**
  - 사용자가 이메일과 비밀번호로 가입한다
- **엣지 케이스:**
  - 이미 가입된 이메일로 가입 시도

### FR-002: 상품 검색
- **설명:** 키워드로 상품을 검색할 수 있다

## 비기능 요구사항

### NFR-001: 성능
- **설명:** 응답 시간 500ms 이내
- **수용 기준:** p99 < 500ms

## 미결 사항

### UR-001
- **질문:** 결제 수단은?
"""

MOCK_TASKS_RESPONSE = """\
```yaml
tasks:
  - id: "TASK-001"
    title: "User 엔티티 정의"
    description: "사용자 회원가입을 위한 User 모델 정의"
    layer: "entity"
    priority: "high"
    estimated_hours: 1.0
    files_changed:
      - "src/models/user.py"
    depends_on: []
  - id: "TASK-002"
    title: "회원가입 서비스 구현"
    description: "이메일 기반 회원가입 비즈니스 로직"
    layer: "service"
    priority: "high"
    estimated_hours: 2.0
    files_changed:
      - "src/services/auth.py"
    depends_on:
      - "TASK-001"
  - id: "TASK-003"
    title: "상품 검색 테스트"
    description: "검색 기능 유닛테스트"
    layer: "test"
    priority: "medium"
    estimated_hours: 1.0
    files_changed:
      - "tests/test_search.py"
    depends_on: []
```
"""


class MockLLM:
    """테스트용 Mock LLM."""

    def __init__(self, response: str = MOCK_TASKS_RESPONSE) -> None:
        self._response = response
        self.call_count = 0

    async def generate(self, prompt: str, *, system: str = "") -> str:
        """Mock LLM 응답 반환."""
        self.call_count += 1
        return self._response


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------


class TestParseRequirementsMd:
    """requirements.md 파싱 테스트."""

    def test_parse_summary(self) -> None:
        """프로젝트 요약을 추출한다."""
        result = parse_requirements_md(SAMPLE_REQUIREMENTS_MD)
        assert "온라인 쇼핑몰" in result.summary

    def test_parse_sections(self) -> None:
        """섹션을 올바르게 추출한다."""
        result = parse_requirements_md(SAMPLE_REQUIREMENTS_MD)
        ids = [s.id for s in result.sections]
        assert "FR-001" in ids
        assert "FR-002" in ids
        assert "NFR-001" in ids
        assert "UR-001" in ids

    def test_section_types(self) -> None:
        """섹션 유형을 올바르게 감지한다."""
        result = parse_requirements_md(SAMPLE_REQUIREMENTS_MD)
        type_map = {s.id: s.section_type for s in result.sections}
        assert type_map["FR-001"] == "functional"
        assert type_map["NFR-001"] == "non_functional"
        assert type_map["UR-001"] == "unresolved"

    def test_empty_input_raises(self) -> None:
        """빈 입력 시 ValueError를 발생시킨다."""
        with pytest.raises(ValueError, match="비어 있습니다"):
            parse_requirements_md("")

    def test_whitespace_only_raises(self) -> None:
        """공백만 있는 입력 시 ValueError를 발생시킨다."""
        with pytest.raises(ValueError, match="비어 있습니다"):
            parse_requirements_md("   \n  ")

    def test_raw_text_preserved(self) -> None:
        """원본 텍스트가 보존된다."""
        result = parse_requirements_md(SAMPLE_REQUIREMENTS_MD)
        assert result.raw_text == SAMPLE_REQUIREMENTS_MD


# ---------------------------------------------------------------------------
# Generator Tests
# ---------------------------------------------------------------------------


class TestParseTasksResponse:
    """LLM 응답 파싱 테스트."""

    def test_parse_valid_response(self) -> None:
        """유효한 YAML 응답을 파싱한다."""
        tasks = _parse_tasks_response(MOCK_TASKS_RESPONSE)
        assert len(tasks) == 3
        assert tasks[0].id == "TASK-001"
        assert tasks[0].layer == TaskLayer.ENTITY

    def test_parse_invalid_yaml(self) -> None:
        """잘못된 YAML은 빈 리스트를 반환한다."""
        tasks = _parse_tasks_response("not yaml at all {{{")
        assert tasks == []

    def test_parse_empty_response(self) -> None:
        """빈 응답은 빈 리스트를 반환한다."""
        tasks = _parse_tasks_response("")
        assert tasks == []

    def test_invalid_layer_defaults(self) -> None:
        """유효하지 않은 layer는 service로 기본 설정된다."""
        response = '```yaml\ntasks:\n  - id: "T-1"\n    title: "x"\n    layer: "unknown"\n```'
        tasks = _parse_tasks_response(response)
        assert tasks[0].layer == TaskLayer.SERVICE

    def test_invalid_priority_defaults(self) -> None:
        """유효하지 않은 priority는 medium으로 기본 설정된다."""
        response = '```yaml\ntasks:\n  - id: "T-1"\n    title: "x"\n    layer: "entity"\n    priority: "critical"\n```'
        tasks = _parse_tasks_response(response)
        assert tasks[0].priority == TaskPriority.MEDIUM


class TestAssignQaTaskIds:
    """qa_task_id 자동 부여 테스트."""

    def test_assigns_qa_ids(self) -> None:
        """구현 작업에 QA Task ID를 부여한다."""
        tasks = [
            Task(id="TASK-001", title="엔티티", layer=TaskLayer.ENTITY),
            Task(id="TASK-002", title="서비스", layer=TaskLayer.SERVICE),
        ]
        result = assign_qa_task_ids(tasks)
        assert result[0].qa_task_id == "TASK-001-QA"
        assert result[1].qa_task_id == "TASK-002-QA"

    def test_skips_test_layer(self) -> None:
        """test 레이어 작업에는 QA ID를 부여하지 않는다."""
        tasks = [
            Task(id="TASK-003", title="테스트", layer=TaskLayer.TEST),
        ]
        result = assign_qa_task_ids(tasks)
        assert result[0].qa_task_id is None

    def test_preserves_existing_qa_id(self) -> None:
        """이미 qa_task_id가 있으면 덮어쓰지 않는다."""
        tasks = [
            Task(id="TASK-001", title="엔티티", layer=TaskLayer.ENTITY, qa_task_id="CUSTOM-QA"),
        ]
        result = assign_qa_task_ids(tasks)
        assert result[0].qa_task_id == "CUSTOM-QA"


class TestRenderTasksYaml:
    """tasks.yaml 렌더링 테스트."""

    def test_renders_valid_yaml(self) -> None:
        """유효한 YAML을 생성한다."""
        tf = TasksFile(tasks=[
            Task(id="TASK-001", title="테스트", layer=TaskLayer.ENTITY),
        ])
        result = render_tasks_yaml(tf)
        data = yaml.safe_load(result)
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == "TASK-001"

    def test_empty_tasks(self) -> None:
        """빈 작업 목록도 유효한 YAML이다."""
        tf = TasksFile(tasks=[])
        result = render_tasks_yaml(tf)
        data = yaml.safe_load(result)
        assert data["tasks"] == []


class TestGenerateTasks:
    """generate_tasks 통합 테스트."""

    def test_generate_tasks(self) -> None:
        """LLM 응답을 파싱하여 TasksFile을 생성한다."""
        llm = MockLLM()
        result = asyncio.get_event_loop().run_until_complete(
            generate_tasks(llm, SAMPLE_REQUIREMENTS_MD)
        )
        assert isinstance(result, TasksFile)
        assert len(result.tasks) == 3
        # qa_task_id 확인
        assert result.tasks[0].qa_task_id == "TASK-001-QA"
        assert result.tasks[2].qa_task_id is None  # test layer

    def test_empty_requirements_raises(self) -> None:
        """빈 requirements는 ValueError를 발생시킨다."""
        llm = MockLLM()
        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                generate_tasks(llm, "")
            )


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestReviewTasksCli:
    """CLI 검수 인터페이스 테스트."""

    def test_approve(self) -> None:
        """Y 입력 시 True를 반환한다."""
        with patch("builtins.input", return_value="Y"):
            assert review_tasks_cli("tasks: []") is True

    def test_reject(self) -> None:
        """N 입력 시 False를 반환한다."""
        with patch("builtins.input", return_value="n"):
            assert review_tasks_cli("tasks: []") is False

    def test_eof_returns_false(self) -> None:
        """EOF 시 False를 반환한다."""
        with patch("builtins.input", side_effect=EOFError):
            assert review_tasks_cli("tasks: []") is False

    def test_invalid_then_valid(self) -> None:
        """잘못된 입력 후 유효한 입력을 처리한다."""
        with patch("builtins.input", side_effect=["maybe", "yes"]):
            assert review_tasks_cli("tasks: []") is True


# ---------------------------------------------------------------------------
# Agent Integration Tests
# ---------------------------------------------------------------------------


class TestTaskGenerationAgent:
    """TaskGenerationAgent 통합 테스트."""

    def test_run_auto_approve(self) -> None:
        """review_fn 없이 실행 시 자동 승인된다."""
        llm = MockLLM()
        agent = TaskGenerationAgent(llm)
        tasks_file, yaml_str = asyncio.get_event_loop().run_until_complete(
            agent.run(SAMPLE_REQUIREMENTS_MD)
        )
        assert isinstance(tasks_file, TasksFile)
        assert len(tasks_file.tasks) == 3
        assert "TASK-001" in yaml_str

    def test_run_with_approval(self) -> None:
        """검수 승인 시 정상 반환한다."""
        llm = MockLLM()
        agent = TaskGenerationAgent(llm)
        tasks_file, yaml_str = asyncio.get_event_loop().run_until_complete(
            agent.run(SAMPLE_REQUIREMENTS_MD, review_fn=lambda _: True)
        )
        assert len(tasks_file.tasks) == 3

    def test_run_max_retries_exceeded(self) -> None:
        """최대 재시도 초과 시 RuntimeError를 발생시킨다."""
        llm = MockLLM()
        agent = TaskGenerationAgent(llm, max_retries=2)
        with pytest.raises(RuntimeError, match="2회 거부"):
            asyncio.get_event_loop().run_until_complete(
                agent.run(SAMPLE_REQUIREMENTS_MD, review_fn=lambda _: False)
            )
        assert llm.call_count == 2

    def test_run_empty_requirements_raises(self) -> None:
        """빈 requirements.md 시 ValueError를 발생시킨다."""
        llm = MockLLM()
        agent = TaskGenerationAgent(llm)
        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                agent.run("")
            )
