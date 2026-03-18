"""PRM 오케스트레이터 — Agent 1→2→3→4 순차 호출.

Closes #41
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from agentcrew.agents.agent1 import RequirementsAgent, LLMProvider
from agentcrew.agents.agent2 import TaskGenerationAgent
from agentcrew.agents.agent3 import CodeImplementationAgent
from agentcrew.agents.agent4 import QAVerificationAgent
from agentcrew.prm.context_injector import ContextInjector
from agentcrew.prm.failure_handler import FailureHandler, PipelineAbortError
from agentcrew.prm.progress_monitor import ProgressMonitor
from agentcrew.notification.dispatcher import NotificationDispatcher
from agentcrew.schemas.config import NotificationConfig
from agentcrew.schemas.progress import PipelineStatus

logger = logging.getLogger(__name__)


@dataclass
class AgentModels:
    """Agent별 LLM 프로바이더 설정."""

    agent1_llm: LLMProvider
    agent2_llm: LLMProvider
    agent3_llm: LLMProvider
    agent4_llm: LLMProvider


@dataclass
class PipelineConfig:
    """파이프라인 실행 설정.

    Args:
        project_root: 프로젝트 루트 디렉토리.
        progress_path: progress.json 경로.
        tasks_yaml_path: tasks.yaml 경로.
        requirements_md_path: requirements.md 경로.
        log_dir: 파이프라인 로그 디렉토리.
        skip_build: 빌드 건너뛰기 (테스트용).
        skip_git: Git 작업 건너뛰기 (테스트용).
        skip_gradle: Gradle 테스트 건너뛰기 (테스트용).
        skip_curl: curl 테스트 건너뛰기 (테스트용).
    """

    project_root: str = "."
    progress_path: str = "progress.json"
    tasks_yaml_path: str = "tasks.yaml"
    requirements_md_path: str = "requirements.md"
    log_dir: str = "pipeline-logs"
    skip_build: bool = False
    skip_git: bool = False
    skip_gradle: bool = False
    skip_curl: bool = False


class PRMOrchestrator:
    """PRM 오케스트레이터.

    Agent 1→2→3→4를 순차적으로 호출하여
    전체 파이프라인을 오케스트레이션한다.

    Args:
        models: Agent별 LLM 프로바이더.
        config: 파이프라인 실행 설정.
    """

    def __init__(
        self,
        models: AgentModels,
        config: Optional[PipelineConfig] = None,
        notification_config: Optional[NotificationConfig] = None,
    ) -> None:
        self.models = models
        self.config = config or PipelineConfig()
        self.monitor = ProgressMonitor(self.config.progress_path)
        self.failure_handler = FailureHandler(log_dir=self.config.log_dir)
        self.context_injector = ContextInjector(self.config.project_root)
        self.dispatcher = NotificationDispatcher(
            notification_config or NotificationConfig()
        )

        # Agent 인스턴스 생성
        self._agent1 = RequirementsAgent(llm=models.agent1_llm)
        self._agent2 = TaskGenerationAgent(llm=models.agent2_llm)
        self._agent3 = CodeImplementationAgent(
            llm=models.agent3_llm,
            project_root=self.config.project_root,
        )
        self._agent4 = QAVerificationAgent(
            llm=models.agent4_llm,
            project_root=self.config.project_root,
        )

    async def run(
        self,
        input_text: str,
        *,
        ask_user=None,
    ) -> dict[str, Any]:
        """전체 파이프라인을 실행한다.

        Agent 1→2→3→4를 순차 호출하며,
        실패 시 중단하고 로그를 저장한다.

        Args:
            input_text: 원본 요구사항 텍스트.
            ask_user: Agent 1 핑퐁 콜백 (선택).

        Returns:
            각 Agent 실행 결과를 담은 딕셔너리.

        Raises:
            PipelineAbortError: 파이프라인 실패 시.
        """
        results: dict[str, Any] = {}
        project_root = Path(self.config.project_root)

        try:
            # === Agent 1: 요구사항 구체화 ===
            results["agent1"] = await self._run_agent1(input_text, ask_user=ask_user)
            requirements_md = results["agent1"]["requirements_md"]

            # requirements.md 저장
            req_path = project_root / self.config.requirements_md_path
            req_path.write_text(requirements_md, encoding="utf-8")

            # === Agent 2: 작업 목록 생성 ===
            context = self.context_injector.load_context("agent2")
            results["agent2"] = await self._run_agent2(requirements_md)

            tasks_yaml = results["agent2"]["tasks_yaml"]
            # tasks.yaml 저장
            tasks_path = project_root / self.config.tasks_yaml_path
            tasks_path.write_text(tasks_yaml, encoding="utf-8")

            # === Agent 3: 코드 구현 ===
            results["agent3"] = await self._run_agent3()

            # === Agent 4: QA 검증 ===
            results["agent4"] = await self._run_agent4()

            # 성공
            self.monitor.mark_success()
            self.failure_handler.add_log("pipeline", "INFO", "파이프라인 완료")
            self.failure_handler.save_logs(suffix="_success")
            await self.dispatcher.notify_success()

        except PipelineAbortError:
            raise
        except Exception as e:
            agent_name = self.monitor.load().current_agent or "unknown"
            await self._handle_failure(agent_name, str(e))

        return results

    async def _run_agent1(
        self,
        input_text: str,
        *,
        ask_user=None,
    ) -> dict[str, Any]:
        """Agent 1을 실행한다."""
        agent_name = "agent1"
        self.monitor.update_agent_start(agent_name)
        self.failure_handler.add_log(agent_name, "INFO", "요구사항 구체화 시작")

        try:
            doc, md = await self._agent1.run(input_text, ask_user=ask_user)
            self.monitor.update_agent_done(agent_name)
            self.failure_handler.add_log(agent_name, "INFO", "요구사항 구체화 완료")
            return {"doc": doc, "requirements_md": md}
        except Exception as e:
            await self._handle_failure(agent_name, str(e))
            raise  # unreachable, _handle_failure raises

    async def _run_agent2(self, requirements_md: str) -> dict[str, Any]:
        """Agent 2를 실행한다."""
        agent_name = "agent2"
        self.monitor.update_agent_start(agent_name)
        self.failure_handler.add_log(agent_name, "INFO", "작업 목록 생성 시작")

        try:
            tasks_file, yaml_str = await self._agent2.run(requirements_md)
            self.monitor.update_agent_done(agent_name)
            self.failure_handler.add_log(agent_name, "INFO", "작업 목록 생성 완료")
            return {"tasks_file": tasks_file, "tasks_yaml": yaml_str}
        except Exception as e:
            await self._handle_failure(agent_name, str(e))
            raise

    async def _run_agent3(self) -> dict[str, Any]:
        """Agent 3을 실행한다."""
        agent_name = "agent3"
        self.monitor.update_agent_start(agent_name)
        self.failure_handler.add_log(agent_name, "INFO", "코드 구현 시작")

        try:
            result = await self._agent3.run(
                tasks_yaml_path=str(
                    Path(self.config.project_root) / self.config.tasks_yaml_path
                ),
                progress_json_path=str(
                    Path(self.config.project_root) / self.config.progress_path
                ),
                skip_build=self.config.skip_build,
                skip_git=self.config.skip_git,
            )
            self.monitor.update_agent_done(agent_name)
            self.failure_handler.add_log(agent_name, "INFO", "코드 구현 완료")
            return {"result": result}
        except Exception as e:
            await self._handle_failure(agent_name, str(e))
            raise

    async def _run_agent4(self) -> dict[str, Any]:
        """Agent 4를 실행한다."""
        agent_name = "agent4"
        self.monitor.update_agent_start(agent_name)
        self.failure_handler.add_log(agent_name, "INFO", "QA 검증 시작")

        try:
            result = await self._agent4.run(
                tasks_yaml_path=str(
                    Path(self.config.project_root) / self.config.tasks_yaml_path
                ),
                skip_gradle=self.config.skip_gradle,
                skip_curl=self.config.skip_curl,
            )
            self.monitor.update_agent_done(agent_name)
            self.failure_handler.add_log(agent_name, "INFO", "QA 검증 완료")
            return {"result": result}
        except Exception as e:
            await self._handle_failure(agent_name, str(e))
            raise

    async def _handle_failure(self, agent_name: str, message: str) -> None:
        """실패를 처리하고 PipelineAbortError를 발생시킨다."""
        self.monitor.mark_failed(agent_name, message)
        self.failure_handler.add_log(agent_name, "ERROR", message)
        log_path = self.failure_handler.save_logs(suffix="_failed")
        await self.dispatcher.notify_failure(agent=agent_name, reason=message)
        raise PipelineAbortError(
            agent=agent_name,
            reason=message,
            log_path=log_path,
        )
