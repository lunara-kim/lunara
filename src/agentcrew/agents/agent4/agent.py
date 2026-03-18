"""Agent 4 — QA 검증 에이전트.

구현된 코드의 품질을 검증한다:
1. Gradle 테스트 실행 + 결과 파싱
2. curl 스모크 테스트 시나리오 생성 및 실행
3. QA 보고서 생성
4. 실패 시 Agent 3에 재작업 요청 (최대 2회)
5. tasks.yaml QA Task 상태 갱신
"""

from __future__ import annotations

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent3.context import (
    FileSystemProvider,
    LocalFileSystem,
    collect_context,
)
from agentcrew.agents.agent3.executor import CommandRunner, SubprocessRunner
from agentcrew.agents.agent3.parser import parse_file_blocks
from agentcrew.agents.agent3.task_runner import (
    load_tasks_yaml,
    save_tasks_yaml,
    update_task_status,
)
from agentcrew.agents.agent4.auth import fetch_auth_token
from agentcrew.agents.agent4.curl_runner import (
    CurlTestSummary,
    parse_scenarios,
    run_all_scenarios,
)
from agentcrew.agents.agent4.gradle_parser import GradleTestResult, run_gradle_tests
from agentcrew.agents.agent4.prompts.templates import (
    GENERATE_CURL_TESTS_PROMPT,
    REWORK_REQUEST_PROMPT,
    SYSTEM_PROMPT,
)
from agentcrew.agents.agent4.report import (
    generate_qa_report,
    is_qa_passed,
    save_qa_report,
)
from agentcrew.schemas.task import TaskStatus


class PipelineAbortError(Exception):
    """재작업 최대 횟수 초과로 파이프라인 중단."""


class QAVerificationAgent:
    """QA 검증 에이전트.

    Args:
        llm: LLM 프로바이더 인스턴스.
        project_root: 대상 프로젝트 루트 경로.
        max_rework: QA 실패 시 최대 재작업 횟수. 기본 2.
        fs: 파일 시스템 프로바이더.
        runner: 명령 실행기.
    """

    def __init__(
        self,
        llm: LLMProvider,
        project_root: str,
        *,
        max_rework: int = 2,
        fs: FileSystemProvider | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self._llm = llm
        self._project_root = project_root
        self._max_rework = max_rework
        self._fs = fs or LocalFileSystem()
        self._runner = runner or SubprocessRunner()

    async def run(
        self,
        tasks_yaml_path: str,
        *,
        report_dir: str = "qa-reports",
        skip_gradle: bool = False,
        skip_curl: bool = False,
        auth_url: str = "http://localhost:8080/api/auth/login",
        auth_username: str = "admin",
        auth_password: str = "admin",
    ) -> dict[str, str]:
        """전체 QA 검증 파이프라인을 실행한다.

        resolved 상태의 Task들에 대해 QA를 수행한다.

        Args:
            tasks_yaml_path: tasks.yaml 파일 경로.
            report_dir: QA 보고서 저장 디렉토리.
            skip_gradle: True면 Gradle 테스트 생략.
            skip_curl: True면 curl 테스트 생략.
            auth_url: 인증 엔드포인트 URL.
            auth_username: 인증 사용자명.
            auth_password: 인증 비밀번호.

        Returns:
            {task_id: "qa_pass"|"qa_fail"} 결과 맵.

        Raises:
            PipelineAbortError: 재작업 최대 횟수 초과 시.
        """
        tasks_file = load_tasks_yaml(tasks_yaml_path)
        results: dict[str, str] = {}

        # resolved 상태 Task들 추출
        resolved_tasks = [
            t for t in tasks_file.tasks if t.status == TaskStatus.RESOLVED
        ]

        for task in resolved_tasks:
            rework_count = 0
            qa_passed = False

            while rework_count <= self._max_rework:
                # 1. Gradle 테스트
                gradle_result = self._run_gradle(skip_gradle)

                # 2. curl 스모크 테스트
                curl_summary = await self._run_curl_tests(
                    task, skip_curl, auth_url, auth_username, auth_password
                )

                # 3. QA 판정
                qa_passed = is_qa_passed(gradle_result, curl_summary)

                # 4. QA 보고서 생성
                report = generate_qa_report(task.id, gradle_result, curl_summary)
                report_path = f"{self._project_root}/{report_dir}/{task.id}-qa-report.md"
                save_qa_report(report, report_path)

                if qa_passed:
                    break

                # 5. 재작업 요청
                rework_count += 1
                if rework_count > self._max_rework:
                    # 최대 재작업 횟수 초과 → 파이프라인 중단
                    tasks_file = update_task_status(
                        tasks_file, task.id, TaskStatus.QA_FAIL
                    )
                    save_tasks_yaml(tasks_yaml_path, tasks_file)
                    results[task.id] = "qa_fail"
                    raise PipelineAbortError(
                        f"Task {task.id}: QA 실패 — 재작업 {self._max_rework}회 초과. "
                        f"파이프라인을 중단합니다."
                    )

                # Agent 3 재작업 요청 (LLM으로 코드 수정)
                await self._request_rework(task, gradle_result, curl_summary)

            if qa_passed:
                # QA 통과 → 상태 갱신
                tasks_file = update_task_status(
                    tasks_file, task.id, TaskStatus.QA_PASS
                )
                save_tasks_yaml(tasks_yaml_path, tasks_file)
                results[task.id] = "qa_pass"

        return results

    def _run_gradle(self, skip: bool) -> GradleTestResult:
        """Gradle 테스트를 실행한다."""
        if skip:
            return GradleTestResult(success=True, total=0, passed=0, failed=0)
        return run_gradle_tests(self._runner, self._project_root)

    async def _run_curl_tests(
        self,
        task,
        skip: bool,
        auth_url: str,
        auth_username: str,
        auth_password: str,
    ) -> CurlTestSummary | None:
        """curl 스모크 테스트를 생성하고 실행한다."""
        if skip:
            return None

        # LLM으로 curl 시나리오 생성
        context = collect_context(self._fs, self._project_root, task.files_changed)
        prompt = GENERATE_CURL_TESTS_PROMPT.format(
            task_id=task.id,
            task_title=task.title,
            task_description=task.description,
            task_layer=task.layer,
            files_changed=", ".join(task.files_changed),
            endpoint_definitions=context.get("current_files", ""),
        )

        response = await self._llm.generate(prompt, system=SYSTEM_PROMPT)
        scenarios = parse_scenarios(response)

        if not scenarios:
            return None

        # 인증 토큰 발급 (auth_required 시나리오가 있는 경우)
        auth_token: str | None = None
        if any(s.auth_required for s in scenarios):
            auth_token = fetch_auth_token(
                self._runner,
                self._project_root,
                auth_url=auth_url,
                username=auth_username,
                password=auth_password,
            )

        return run_all_scenarios(
            self._runner,
            scenarios,
            self._project_root,
            auth_token=auth_token,
        )

    async def _request_rework(
        self,
        task,
        gradle_result: GradleTestResult,
        curl_summary: CurlTestSummary | None,
    ) -> None:
        """Agent 3에 재작업을 요청한다 (LLM으로 코드 수정)."""
        # 실패 상세 정보 수집
        failure_details_parts: list[str] = []
        if not gradle_result.success:
            failure_details_parts.append(
                f"Gradle 빌드/테스트 실패:\n{gradle_result.error_output[:1500]}"
            )
            if gradle_result.failed_tests:
                failure_details_parts.append(
                    "실패 테스트: " + ", ".join(gradle_result.failed_tests)
                )

        if curl_summary and not curl_summary.success:
            for r in curl_summary.results:
                if not r.passed:
                    failure_details_parts.append(
                        f"Curl 실패 — {r.scenario_name}: {r.error_message}"
                    )

        failure_details = "\n".join(failure_details_parts)

        # 현재 파일 컨텍스트
        context = collect_context(self._fs, self._project_root, task.files_changed)

        prompt = REWORK_REQUEST_PROMPT.format(
            task_id=task.id,
            failure_details=failure_details,
            current_files=context.get("current_files", ""),
        )

        response = await self._llm.generate(prompt, system=SYSTEM_PROMPT)
        file_blocks = parse_file_blocks(response)

        # 수정된 파일 쓰기
        for path, content in file_blocks.items():
            full_path = f"{self._project_root}/{path}"
            self._fs.write_file(full_path, content)
