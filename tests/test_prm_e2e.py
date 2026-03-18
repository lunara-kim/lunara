"""PRM E2E 통합 테스트.

모든 Agent를 mock LLM으로 연결하여 파이프라인 전체 흐름을 검증한다.

Closes #46
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
import yaml

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.prm.orchestrator import PRMOrchestrator, AgentModels, PipelineConfig
from agentcrew.prm.progress_monitor import ProgressMonitor
from agentcrew.prm.failure_handler import FailureHandler, PipelineAbortError
from agentcrew.prm.context_injector import ContextInjector, DEFAULT_CONTEXT_MAP
from agentcrew.prm.opencode_wrapper import OpenCodeWrapper
from agentcrew.schemas.progress import PipelineStatus


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------


class MockLLM:
    """응답 시퀀스를 순서대로 반환하는 Mock LLM."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self._call_count = 0

    async def generate(self, prompt: str, *, system: str = "") -> str:
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
        else:
            resp = "mock response"
        self._call_count += 1
        return resp


# ---------------------------------------------------------------------------
# Mock LLM 응답 데이터
# ---------------------------------------------------------------------------

MOCK_REQUIREMENTS_RESPONSE = """\
```yaml
summary: "테스트 프로젝트"
functional:
  - id: "FR-001"
    title: "사용자 로그인"
    description: "이메일/비밀번호 기반 로그인"
    priority: "high"
    acceptance_criteria:
      - "이메일과 비밀번호로 로그인할 수 있다"
non_functional:
  - id: "NFR-001"
    title: "응답 시간"
    description: "API 응답 2초 이내"
    category: "performance"
```
"""

MOCK_TASKS_RESPONSE = """\
```yaml
tasks:
  - id: "TASK-001"
    title: "User 엔티티 생성"
    description: "User 엔티티 및 JPA 설정"
    layer: "entity"
    priority: "high"
    estimated_hours: 2.0
    status: "new"
    files_changed:
      - "src/main/java/com/example/entity/User.java"
    depends_on: []
  - id: "TASK-002"
    title: "로그인 API 구현"
    description: "POST /api/auth/login"
    layer: "controller"
    priority: "high"
    estimated_hours: 3.0
    status: "new"
    files_changed:
      - "src/main/java/com/example/controller/AuthController.java"
    depends_on:
      - "TASK-001"
```
"""

MOCK_IMPLEMENT_RESPONSE = """\
```java
// FILE: src/main/java/com/example/entity/User.java
package com.example.entity;

public class User {
    private Long id;
    private String email;
}
```
"""

MOCK_QA_GRADLE_RESPONSE = """\
테스트 결과: 전체 통과
- 총 2개 테스트 실행
- 성공: 2개
- 실패: 0개
"""

MOCK_QA_CURL_RESPONSE = """\
```yaml
scenarios: []
```
"""

MOCK_QA_REPORT_RESPONSE = """\
# QA Report

## 결과: PASS

모든 테스트가 통과했습니다.
"""


# ---------------------------------------------------------------------------
# ProgressMonitor 테스트
# ---------------------------------------------------------------------------


class TestProgressMonitor:
    """ProgressMonitor 유닛테스트."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.json"
        monitor = ProgressMonitor(path)

        progress = monitor.update_agent_start("agent1")
        assert progress.pipeline_status == PipelineStatus.RUNNING
        assert progress.current_agent == "agent1"

        loaded = monitor.load()
        assert loaded.pipeline_status == PipelineStatus.RUNNING

    def test_mark_success(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.json"
        monitor = ProgressMonitor(path)

        monitor.update_agent_start("agent1")
        progress = monitor.mark_success()
        assert progress.pipeline_status == PipelineStatus.SUCCESS
        assert progress.current_agent is None

    def test_mark_failed(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.json"
        monitor = ProgressMonitor(path)

        monitor.update_agent_start("agent2")
        progress = monitor.mark_failed("agent2", "LLM 호출 실패")
        assert progress.pipeline_status == PipelineStatus.FAILED
        assert progress.error is not None
        assert progress.error.agent == "agent2"
        assert "LLM" in progress.error.message

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        monitor = ProgressMonitor(path)
        progress = monitor.load()
        assert progress.pipeline_status == PipelineStatus.IDLE

    @pytest.mark.asyncio
    async def test_poll_until_complete(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.json"
        monitor = ProgressMonitor(path, poll_interval=0.1)

        # 미리 성공 상태로 저장
        monitor.update_agent_start("agent1")
        monitor.mark_success()

        result = await monitor.poll_until_complete(timeout=1.0)
        assert result.pipeline_status == PipelineStatus.SUCCESS


# ---------------------------------------------------------------------------
# FailureHandler 테스트
# ---------------------------------------------------------------------------


class TestFailureHandler:
    """FailureHandler 유닛테스트."""

    def test_add_and_save_logs(self, tmp_path: Path) -> None:
        handler = FailureHandler(log_dir=tmp_path / "logs")
        handler.add_log("agent1", "INFO", "시작")
        handler.add_log("agent1", "ERROR", "실패")

        assert handler.has_errors()
        assert len(handler.logs) == 2

        log_path = handler.save_logs(suffix="_test")
        assert log_path.exists()

        data = json.loads(log_path.read_text())
        assert len(data) == 2
        assert data[1]["level"] == "ERROR"

    def test_no_errors(self, tmp_path: Path) -> None:
        handler = FailureHandler(log_dir=tmp_path)
        handler.add_log("agent1", "INFO", "OK")
        assert not handler.has_errors()


# ---------------------------------------------------------------------------
# ContextInjector 테스트
# ---------------------------------------------------------------------------


class TestContextInjector:
    """ContextInjector 유닛테스트."""

    def test_default_context_map(self, tmp_path: Path) -> None:
        injector = ContextInjector(tmp_path)
        assert injector.get_context_files("agent1") == []
        assert "requirements.md" in injector.get_context_files("agent2")

    def test_load_context(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.md").write_text("# Req", encoding="utf-8")
        injector = ContextInjector(tmp_path)

        ctx = injector.load_context("agent2")
        assert "requirements.md" in ctx
        assert ctx["requirements.md"] == "# Req"

    def test_load_context_missing_file(self, tmp_path: Path) -> None:
        injector = ContextInjector(tmp_path)
        ctx = injector.load_context("agent2")
        assert ctx == {}

    def test_format_context(self, tmp_path: Path) -> None:
        injector = ContextInjector(tmp_path)
        formatted = injector.format_context({"a.txt": "hello", "b.txt": "world"})
        assert "--- a.txt ---" in formatted
        assert "hello" in formatted

    def test_add_context_file(self, tmp_path: Path) -> None:
        injector = ContextInjector(tmp_path)
        injector.add_context_file("agent1", "extra.md")
        assert "extra.md" in injector.get_context_files("agent1")


# ---------------------------------------------------------------------------
# OpenCodeWrapper 테스트
# ---------------------------------------------------------------------------


class TestOpenCodeWrapper:
    """OpenCodeWrapper 유닛테스트."""

    def test_build_command(self) -> None:
        wrapper = OpenCodeWrapper(binary="/usr/bin/opencode", default_model="gpt-4o")
        cmd = wrapper._build_command("hello", model="claude-3")
        assert "/usr/bin/opencode" in cmd
        assert "--model" in cmd
        assert "claude-3" in cmd
        assert "--prompt" in cmd
        assert "hello" in cmd

    def test_build_command_default_model(self) -> None:
        wrapper = OpenCodeWrapper(default_model="gpt-4o")
        cmd = wrapper._build_command("test")
        assert "gpt-4o" in cmd

    @pytest.mark.asyncio
    async def test_run_binary_not_found(self) -> None:
        wrapper = OpenCodeWrapper(binary="/nonexistent/opencode")
        result = await wrapper.run("test prompt")
        assert not result.success
        assert "not found" in result.stderr.lower() or result.returncode == -1


# ---------------------------------------------------------------------------
# PRMOrchestrator E2E 테스트
# ---------------------------------------------------------------------------


class TestPRMOrchestratorE2E:
    """PRMOrchestrator E2E 통합 테스트 (mock LLM)."""

    def _make_models(self) -> AgentModels:
        """Agent별 Mock LLM을 생성한다."""
        return AgentModels(
            agent1_llm=MockLLM([MOCK_REQUIREMENTS_RESPONSE]),
            agent2_llm=MockLLM([MOCK_TASKS_RESPONSE]),
            agent3_llm=MockLLM([MOCK_IMPLEMENT_RESPONSE] * 10),
            agent4_llm=MockLLM([
                MOCK_QA_GRADLE_RESPONSE,
                MOCK_QA_CURL_RESPONSE,
                MOCK_QA_REPORT_RESPONSE,
            ] * 5),
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, tmp_path: Path) -> None:
        """Agent 1→2→3→4 전체 파이프라인이 성공적으로 동작한다."""
        config = PipelineConfig(
            project_root=str(tmp_path),
            progress_path=str(tmp_path / "progress.json"),
            tasks_yaml_path=str(tmp_path / "tasks.yaml"),
            requirements_md_path=str(tmp_path / "requirements.md"),
            log_dir=str(tmp_path / "logs"),
            skip_build=True,
            skip_git=True,
            skip_gradle=True,
            skip_curl=True,
        )

        orchestrator = PRMOrchestrator(
            models=self._make_models(),
            config=config,
        )

        results = await orchestrator.run("온라인 쇼핑몰을 만들어주세요")

        # Agent 1 결과 검증
        assert "agent1" in results
        assert "requirements_md" in results["agent1"]

        # Agent 2 결과 검증
        assert "agent2" in results
        assert "tasks_yaml" in results["agent2"]

        # requirements.md 파일 생성 확인
        assert (tmp_path / "requirements.md").exists()

        # progress.json 최종 상태 확인
        monitor = ProgressMonitor(tmp_path / "progress.json")
        progress = monitor.load()
        assert progress.pipeline_status == PipelineStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_pipeline_failure_at_agent1(self, tmp_path: Path) -> None:
        """Agent 1에서 실패 시 파이프라인이 중단되고 로그가 저장된다."""

        class FailingLLM:
            async def generate(self, prompt: str, *, system: str = "") -> str:
                raise RuntimeError("LLM API 오류")

        config = PipelineConfig(
            project_root=str(tmp_path),
            progress_path=str(tmp_path / "progress.json"),
            tasks_yaml_path=str(tmp_path / "tasks.yaml"),
            requirements_md_path=str(tmp_path / "requirements.md"),
            log_dir=str(tmp_path / "logs"),
            skip_build=True,
            skip_git=True,
        )

        models = AgentModels(
            agent1_llm=FailingLLM(),
            agent2_llm=MockLLM(),
            agent3_llm=MockLLM(),
            agent4_llm=MockLLM(),
        )

        orchestrator = PRMOrchestrator(models=models, config=config)

        with pytest.raises(PipelineAbortError) as exc_info:
            await orchestrator.run("실패 테스트")

        assert exc_info.value.agent == "agent1"
        assert exc_info.value.log_path is not None
        assert exc_info.value.log_path.exists()

        # progress.json이 FAILED 상태인지 확인
        monitor = ProgressMonitor(tmp_path / "progress.json")
        progress = monitor.load()
        assert progress.pipeline_status == PipelineStatus.FAILED

    @pytest.mark.asyncio
    async def test_context_injection_during_pipeline(self, tmp_path: Path) -> None:
        """파이프라인 실행 중 컨텍스트가 올바르게 주입되는지 확인한다."""
        config = PipelineConfig(
            project_root=str(tmp_path),
            progress_path=str(tmp_path / "progress.json"),
            tasks_yaml_path=str(tmp_path / "tasks.yaml"),
            requirements_md_path=str(tmp_path / "requirements.md"),
            log_dir=str(tmp_path / "logs"),
            skip_build=True,
            skip_git=True,
            skip_gradle=True,
            skip_curl=True,
        )

        orchestrator = PRMOrchestrator(
            models=self._make_models(),
            config=config,
        )

        # 컨텍스트 주입기 검증
        injector = orchestrator.context_injector
        assert injector.get_context_files("agent2") == ["requirements.md"]
        assert "tasks.yaml" in injector.get_context_files("agent3")

    @pytest.mark.asyncio
    async def test_progress_tracking_during_pipeline(self, tmp_path: Path) -> None:
        """파이프라인 실행 중 progress.json이 갱신되는지 확인한다."""
        config = PipelineConfig(
            project_root=str(tmp_path),
            progress_path=str(tmp_path / "progress.json"),
            tasks_yaml_path=str(tmp_path / "tasks.yaml"),
            requirements_md_path=str(tmp_path / "requirements.md"),
            log_dir=str(tmp_path / "logs"),
            skip_build=True,
            skip_git=True,
            skip_gradle=True,
            skip_curl=True,
        )

        orchestrator = PRMOrchestrator(
            models=self._make_models(),
            config=config,
        )

        await orchestrator.run("테스트 입력")

        # 로그 파일이 생성되었는지 확인
        log_files = list((tmp_path / "logs").glob("*.json"))
        assert len(log_files) >= 1
