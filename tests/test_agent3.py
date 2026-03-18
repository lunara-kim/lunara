"""Agent 3 유닛테스트."""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path
from typing import Optional

import pytest
import yaml

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent3.agent import CodeImplementationAgent
from agentcrew.agents.agent3.context import collect_context, LocalFileSystem
from agentcrew.agents.agent3.executor import CommandResult, CommandRunner, GradleRunner, GitRunner
from agentcrew.agents.agent3.parser import parse_file_blocks
from agentcrew.agents.agent3.prompts.templates import (
    FIX_BUILD_PROMPT,
    IMPLEMENT_TASK_PROMPT,
    SYSTEM_PROMPT,
)
from agentcrew.agents.agent3.task_runner import (
    get_pending_tasks,
    load_tasks_yaml,
    record_build_error,
    save_tasks_yaml,
    update_task_status,
    load_progress,
    save_progress,
)
from agentcrew.schemas.progress import Progress, PipelineStatus
from agentcrew.schemas.task import Task, TaskLayer, TaskPriority, TaskStatus, TasksFile


# ---------------------------------------------------------------------------
# Fixtures & Mocks
# ---------------------------------------------------------------------------

SAMPLE_TASKS_YAML = {
    "tasks": [
        {
            "id": "TASK-001",
            "title": "User 엔티티 생성",
            "description": "User 엔티티를 생성한다",
            "layer": "entity",
            "priority": "high",
            "estimated_hours": 1.0,
            "status": "new",
            "files_changed": ["src/main/java/com/example/User.java"],
            "depends_on": [],
        },
        {
            "id": "TASK-002",
            "title": "UserRepository 생성",
            "description": "UserRepository를 생성한다",
            "layer": "repository",
            "priority": "medium",
            "estimated_hours": 1.0,
            "status": "new",
            "files_changed": ["src/main/java/com/example/UserRepository.java"],
            "depends_on": ["TASK-001"],
        },
    ]
}

LLM_IMPLEMENT_RESPONSE = """\
===FILE: src/main/java/com/example/User.java===
package com.example;

public class User {
    private Long id;
    private String name;
}
===END_FILE===
"""

LLM_FIX_RESPONSE = """\
===FILE: src/main/java/com/example/User.java===
package com.example;

public class User {
    private Long id;
    private String name;
    private String email;
}
===END_FILE===
"""


class FakeLLM:
    """테스트용 LLM."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [LLM_IMPLEMENT_RESPONSE])
        self._call_count = 0
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, system: str = "") -> str:
        self.prompts.append(prompt)
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]


class FakeRunner:
    """테스트용 CommandRunner."""

    def __init__(self, results: list[CommandResult] | None = None) -> None:
        self._results = list(results or [CommandResult(0, "BUILD SUCCESSFUL", "")])
        self._call_count = 0
        self.commands: list[list[str]] = []

    def run(self, args: list[str], cwd: str) -> CommandResult:
        self.commands.append(args)
        idx = min(self._call_count, len(self._results) - 1)
        self._call_count += 1
        return self._results[idx]


class FakeFS:
    """테스트용 파일 시스템."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files: dict[str, str] = dict(files or {})

    def read_file(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def write_file(self, path: str, content: str) -> None:
        self.files[path] = content

    def list_tree(self, root: str, max_depth: int = 3) -> str:
        return "src/\n  main/\n    java/"

    def exists(self, path: str) -> bool:
        return path in self.files


# ---------------------------------------------------------------------------
# Tests: parser
# ---------------------------------------------------------------------------

class TestParseFileBlocks:
    def test_single_file(self) -> None:
        blocks = parse_file_blocks(LLM_IMPLEMENT_RESPONSE)
        assert "src/main/java/com/example/User.java" in blocks
        assert "package com.example;" in blocks["src/main/java/com/example/User.java"]

    def test_multiple_files(self) -> None:
        response = (
            "===FILE: a.java===\nclass A {}\n===END_FILE===\n"
            "===FILE: b.java===\nclass B {}\n===END_FILE==="
        )
        blocks = parse_file_blocks(response)
        assert len(blocks) == 2
        assert "class A {}" in blocks["a.java"]
        assert "class B {}" in blocks["b.java"]

    def test_empty_response(self) -> None:
        assert parse_file_blocks("no files here") == {}


# ---------------------------------------------------------------------------
# Tests: context
# ---------------------------------------------------------------------------

class TestCollectContext:
    def test_collects_build_gradle(self) -> None:
        fs = FakeFS({"/project/build.gradle": "plugins { id 'java' }"})
        ctx = collect_context(fs, "/project", [])
        assert "plugins" in ctx["build_gradle"]

    def test_collects_existing_files(self) -> None:
        fs = FakeFS({
            "/project/src/A.java": "class A {}",
        })
        ctx = collect_context(fs, "/project", ["src/A.java"])
        assert "class A {}" in ctx["current_files"]

    def test_missing_files_ignored(self) -> None:
        fs = FakeFS({})
        ctx = collect_context(fs, "/project", ["nonexistent.java"])
        assert ctx["current_files"] == ""
        assert ctx["build_gradle"] == ""


# ---------------------------------------------------------------------------
# Tests: task_runner
# ---------------------------------------------------------------------------

class TestTaskRunner:
    def test_load_save_tasks_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "tasks.yaml"
        p.write_text(yaml.dump(SAMPLE_TASKS_YAML), encoding="utf-8")
        tf = load_tasks_yaml(str(p))
        assert len(tf.tasks) == 2
        assert tf.tasks[0].id == "TASK-001"

        save_tasks_yaml(str(p), tf)
        tf2 = load_tasks_yaml(str(p))
        assert tf2.tasks[0].id == "TASK-001"

    def test_update_task_status(self) -> None:
        tf = TasksFile(tasks=[
            Task(id="T-1", title="test", layer=TaskLayer.ENTITY, status=TaskStatus.NEW),
        ])
        updated = update_task_status(tf, "T-1", TaskStatus.IN_PROGRESS)
        assert updated.tasks[0].status == TaskStatus.IN_PROGRESS

    def test_get_pending_tasks_sorted(self) -> None:
        tf = TasksFile(tasks=[
            Task(id="T-1", title="low", layer=TaskLayer.ENTITY, priority=TaskPriority.LOW),
            Task(id="T-2", title="high", layer=TaskLayer.ENTITY, priority=TaskPriority.HIGH),
            Task(id="T-3", title="done", layer=TaskLayer.ENTITY, status=TaskStatus.RESOLVED),
        ])
        pending = get_pending_tasks(tf)
        assert len(pending) == 2
        assert pending[0].id == "T-2"  # high first

    def test_record_build_error(self) -> None:
        progress = Progress()
        updated = record_build_error(progress, "T-1", "compile error", 3)
        assert updated.error is not None
        assert updated.error.agent == "agent3"
        assert "T-1" in updated.error.message
        assert updated.error.retry_count == 3


# ---------------------------------------------------------------------------
# Tests: executor
# ---------------------------------------------------------------------------

class TestExecutor:
    def test_gradle_runner(self) -> None:
        fake = FakeRunner([CommandResult(0, "OK", "")])
        gradle = GradleRunner(fake, "/project")
        result = gradle.build_and_test()
        assert result.success
        assert fake.commands[0] == ["./gradlew", "build", "--no-daemon"]

    def test_git_runner_create_branch(self) -> None:
        fake = FakeRunner([CommandResult(0, "", "")])
        git = GitRunner(fake, "/project")
        result = git.create_branch("feature/test")
        assert result.success

    def test_git_runner_add_and_commit(self) -> None:
        fake = FakeRunner([CommandResult(0, "", "")] * 3)
        git = GitRunner(fake, "/project")
        result = git.add_and_commit(["a.java", "b.java"], "feat: test")
        assert result.success
        # 2 adds + 1 commit = 3 commands
        assert len(fake.commands) == 3

    def test_git_branch_exists(self) -> None:
        fake = FakeRunner([CommandResult(0, "", "")])
        git = GitRunner(fake, "/project")
        assert git.branch_exists("main") is True

    def test_git_branch_not_exists(self) -> None:
        fake = FakeRunner([CommandResult(128, "", "not found")])
        git = GitRunner(fake, "/project")
        assert git.branch_exists("nope") is False


# ---------------------------------------------------------------------------
# Tests: prompts
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_system_prompt_exists(self) -> None:
        assert len(SYSTEM_PROMPT) > 0

    def test_implement_prompt_format(self) -> None:
        result = IMPLEMENT_TASK_PROMPT.format(
            task_id="T-1",
            task_title="Test",
            task_description="Desc",
            task_layer="entity",
            files_changed="A.java",
            build_gradle="plugins {}",
            directory_tree="src/",
        )
        assert "T-1" in result
        assert "plugins {}" in result

    def test_fix_prompt_format(self) -> None:
        result = FIX_BUILD_PROMPT.format(
            task_id="T-1",
            error_output="compilation failed",
            current_files="===FILE: A.java===\n...\n===END_FILE===",
        )
        assert "compilation failed" in result


# ---------------------------------------------------------------------------
# Tests: agent integration
# ---------------------------------------------------------------------------

class TestCodeImplementationAgent:
    def test_run_skip_build_and_git(self, tmp_path: Path) -> None:
        """빌드/Git 생략 모드로 전체 파이프라인 테스트."""
        tasks_path = tmp_path / "tasks.yaml"
        tasks_path.write_text(yaml.dump(SAMPLE_TASKS_YAML), encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("{}", encoding="utf-8")

        fs = FakeFS({
            "/project/build.gradle": "plugins { id 'java' }",
        })
        llm = FakeLLM([LLM_IMPLEMENT_RESPONSE, LLM_IMPLEMENT_RESPONSE])

        agent = CodeImplementationAgent(
            llm=llm,
            project_root="/project",
            fs=fs,
            runner=FakeRunner(),
        )

        results = asyncio.run(agent.run(
            str(tasks_path),
            str(progress_path),
            skip_build=True,
            skip_git=True,
        ))

        assert results["TASK-001"] == "resolved"
        assert results["TASK-002"] == "resolved"

        # tasks.yaml 상태 확인
        tf = load_tasks_yaml(str(tasks_path))
        for t in tf.tasks:
            assert t.status == TaskStatus.RESOLVED

    def test_run_build_failure_then_fix(self, tmp_path: Path) -> None:
        """빌드 1회 실패 후 수정 성공 테스트."""
        tasks_yaml = {"tasks": [SAMPLE_TASKS_YAML["tasks"][0]]}
        tasks_path = tmp_path / "tasks.yaml"
        tasks_path.write_text(yaml.dump(tasks_yaml), encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("{}", encoding="utf-8")

        fs = FakeFS({"/project/build.gradle": "plugins {}"})
        # LLM: 구현 → 수정
        llm = FakeLLM([LLM_IMPLEMENT_RESPONSE, LLM_FIX_RESPONSE])
        # Build: fail → success
        runner = FakeRunner([
            # git branch_exists
            CommandResult(128, "", ""),
            # git create_branch
            CommandResult(0, "", ""),
            # gradle fail
            CommandResult(1, "FAILURE", "compile error"),
            # gradle success
            CommandResult(0, "SUCCESS", ""),
            # git add
            CommandResult(0, "", ""),
            # git add (tasks.yaml)
            CommandResult(0, "", ""),
            # git commit
            CommandResult(0, "", ""),
        ])

        agent = CodeImplementationAgent(
            llm=llm,
            project_root="/project",
            fs=fs,
            runner=runner,
        )

        results = asyncio.run(agent.run(
            str(tasks_path),
            str(progress_path),
            epic_id="test-epic",
        ))
        assert results["TASK-001"] == "resolved"

    def test_run_build_failure_exceeds_max_retries(self, tmp_path: Path) -> None:
        """빌드 3회 실패 시 에러 기록 테스트."""
        tasks_yaml = {"tasks": [SAMPLE_TASKS_YAML["tasks"][0]]}
        tasks_path = tmp_path / "tasks.yaml"
        tasks_path.write_text(yaml.dump(tasks_yaml), encoding="utf-8")
        progress_path = tmp_path / "progress.json"
        progress_path.write_text("{}", encoding="utf-8")

        fs = FakeFS({"/project/build.gradle": "plugins {}"})
        # LLM: 구현 + 2회 수정 시도
        llm = FakeLLM([LLM_IMPLEMENT_RESPONSE, LLM_FIX_RESPONSE, LLM_FIX_RESPONSE])
        # 모든 빌드 실패 + git 명령
        runner = FakeRunner([
            CommandResult(128, "", ""),  # branch_exists
            CommandResult(0, "", ""),    # create_branch
            CommandResult(1, "", "err"), # gradle fail 1
            CommandResult(1, "", "err"), # gradle fail 2
            CommandResult(1, "", "err"), # gradle fail 3
        ])

        agent = CodeImplementationAgent(
            llm=llm,
            project_root="/project",
            fs=fs,
            runner=runner,
        )

        results = asyncio.run(agent.run(
            str(tasks_path),
            str(progress_path),
            epic_id="fail-epic",
        ))
        assert results["TASK-001"] == "failed"

        # progress.json에 에러 기록 확인
        progress = load_progress(str(progress_path))
        assert progress.error is not None
        assert progress.error.agent == "agent3"
        assert progress.error.retry_count == 3


class TestProgressPersistence:
    def test_load_save_progress(self, tmp_path: Path) -> None:
        p = tmp_path / "progress.json"
        progress = Progress(pipeline_status=PipelineStatus.RUNNING, current_agent="agent3")
        save_progress(str(p), progress)
        loaded = load_progress(str(p))
        assert loaded.pipeline_status == PipelineStatus.RUNNING
        assert loaded.current_agent == "agent3"

    def test_load_nonexistent_progress(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.json"
        progress = load_progress(str(p))
        assert progress.pipeline_status == PipelineStatus.IDLE


class TestLocalFileSystem:
    def test_read_write(self, tmp_path: Path) -> None:
        fs = LocalFileSystem()
        p = str(tmp_path / "test.txt")
        fs.write_file(p, "hello")
        assert fs.read_file(p) == "hello"

    def test_exists(self, tmp_path: Path) -> None:
        fs = LocalFileSystem()
        assert fs.exists(str(tmp_path)) is True
        assert fs.exists(str(tmp_path / "nope")) is False

    def test_list_tree(self, tmp_path: Path) -> None:
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b.txt").write_text("x")
        fs = LocalFileSystem()
        tree = fs.list_tree(str(tmp_path))
        assert "a" in tree
        assert "b.txt" in tree
