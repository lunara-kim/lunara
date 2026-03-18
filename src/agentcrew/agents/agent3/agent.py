"""Agent 3 — 코드 구현 에이전트.

tasks.yaml의 각 Task를 순차적으로 구현하고,
Gradle 빌드/테스트를 실행하여 검증한다.
실패 시 최대 3회 자체 수정 재시도를 수행한다.
"""

from __future__ import annotations

from datetime import date

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent3.context import (
    FileSystemProvider,
    LocalFileSystem,
    collect_context,
)
from agentcrew.agents.agent3.executor import (
    CommandRunner,
    GitRunner,
    GradleRunner,
    SubprocessRunner,
)
from agentcrew.agents.agent3.parser import parse_file_blocks
from agentcrew.agents.agent3.prompts.templates import (
    FIX_BUILD_PROMPT,
    IMPLEMENT_TASK_PROMPT,
    SYSTEM_PROMPT,
)
from agentcrew.agents.agent3.task_runner import (
    get_pending_tasks,
    load_progress,
    load_tasks_yaml,
    record_build_error,
    save_progress,
    save_tasks_yaml,
    update_task_status,
)
from agentcrew.schemas.task import TaskStatus


class CodeImplementationAgent:
    """코드 구현 에이전트.

    tasks.yaml의 Task를 순차적으로 구현하고 빌드/테스트를 수행한다.

    Args:
        llm: LLM 프로바이더 인스턴스.
        project_root: 대상 프로젝트 루트 경로.
        max_retries: 빌드 실패 시 최대 재시도 횟수. 기본 3.
        fs: 파일 시스템 프로바이더. 기본 LocalFileSystem.
        runner: 명령 실행기. 기본 SubprocessRunner.
    """

    def __init__(
        self,
        llm: LLMProvider,
        project_root: str,
        *,
        max_retries: int = 3,
        fs: FileSystemProvider | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self._llm = llm
        self._project_root = project_root
        self._max_retries = max_retries
        self._fs = fs or LocalFileSystem()
        self._runner = runner or SubprocessRunner()
        self._gradle = GradleRunner(self._runner, project_root)
        self._git = GitRunner(self._runner, project_root)

    async def run(
        self,
        tasks_yaml_path: str,
        progress_json_path: str,
        *,
        epic_id: str = "epic",
        skip_build: bool = False,
        skip_git: bool = False,
    ) -> dict[str, str]:
        """전체 구현 파이프라인을 실행한다.

        1. 브랜치 생성
        2. 각 Task를 순차 구현
        3. 빌드/테스트 + 재시도
        4. Task 단위 커밋

        Args:
            tasks_yaml_path: tasks.yaml 파일 경로.
            progress_json_path: progress.json 파일 경로.
            epic_id: Epic ID (브랜치 이름에 사용).
            skip_build: True면 빌드/테스트 생략 (테스트용).
            skip_git: True면 Git 연산 생략 (테스트용).

        Returns:
            {task_id: "resolved"|"failed"} 결과 맵.
        """
        tasks_file = load_tasks_yaml(tasks_yaml_path)
        progress = load_progress(progress_json_path)

        # 브랜치 생성
        if not skip_git:
            branch_name = f"feature/agentcrew-{date.today().isoformat()}-{epic_id}"
            if not self._git.branch_exists(branch_name):
                self._git.create_branch(branch_name)
            else:
                self._git.checkout(branch_name)

        results: dict[str, str] = {}
        pending = get_pending_tasks(tasks_file)

        for task in pending:
            # status → in_progress
            tasks_file = update_task_status(tasks_file, task.id, TaskStatus.IN_PROGRESS)
            save_tasks_yaml(tasks_yaml_path, tasks_file)

            # 컨텍스트 수집 & LLM 구현
            context = collect_context(self._fs, self._project_root, task.files_changed)
            prompt = IMPLEMENT_TASK_PROMPT.format(
                task_id=task.id,
                task_title=task.title,
                task_description=task.description,
                task_layer=task.layer,
                files_changed=", ".join(task.files_changed),
                build_gradle=context["build_gradle"],
                directory_tree=context["directory_tree"],
            )

            response = await self._llm.generate(prompt, system=SYSTEM_PROMPT)
            file_blocks = parse_file_blocks(response)

            # 파일 쓰기
            self._write_files(file_blocks)

            # 빌드/테스트
            build_ok = True
            if not skip_build:
                build_ok = await self._build_with_retries(
                    task.id,
                    task.files_changed,
                    context,
                    progress,
                    progress_json_path,
                )

            if build_ok:
                tasks_file = update_task_status(tasks_file, task.id, TaskStatus.RESOLVED)
                save_tasks_yaml(tasks_yaml_path, tasks_file)
                results[task.id] = "resolved"

                # Git 커밋
                if not skip_git:
                    commit_files = list(file_blocks.keys()) + [tasks_yaml_path]
                    self._git.add_and_commit(
                        commit_files,
                        f"feat: implement {task.id} - {task.title}",
                    )
            else:
                results[task.id] = "failed"
                # 3회 초과 실패 → progress.json error 기록
                progress = record_build_error(
                    progress, task.id, "빌드 3회 초과 실패", self._max_retries
                )
                save_progress(progress_json_path, progress)
                # 실패한 Task는 in_progress 상태로 남음

        return results

    async def _build_with_retries(
        self,
        task_id: str,
        files_changed: list[str],
        context: dict[str, str],
        progress: object,
        progress_json_path: str,
    ) -> bool:
        """빌드/테스트를 최대 max_retries 회 재시도한다."""
        for attempt in range(1, self._max_retries + 1):
            result = self._gradle.build_and_test()
            if result.success:
                return True

            error_output = result.stdout + "\n" + result.stderr
            if attempt >= self._max_retries:
                return False

            # LLM에게 수정 요청
            fix_context = collect_context(self._fs, self._project_root, files_changed)
            fix_prompt = FIX_BUILD_PROMPT.format(
                task_id=task_id,
                error_output=error_output[-3000:],  # 마지막 3000자
                current_files=fix_context["current_files"],
            )
            fix_response = await self._llm.generate(fix_prompt, system=SYSTEM_PROMPT)
            fixed_blocks = parse_file_blocks(fix_response)
            self._write_files(fixed_blocks)

        return False  # pragma: no cover

    def _write_files(self, file_blocks: dict[str, str]) -> None:
        """파일 블록을 디스크에 기록한다."""
        for path, content in file_blocks.items():
            full_path = f"{self._project_root}/{path}"
            self._fs.write_file(full_path, content)
