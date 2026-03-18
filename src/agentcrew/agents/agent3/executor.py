"""외부 프로세스 실행 추상화.

Gradle 빌드/테스트 및 Git 명령 실행을 추상화하여 테스트 가능하게 한다.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CommandResult:
    """명령 실행 결과."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


@runtime_checkable
class CommandRunner(Protocol):
    """외부 명령 실행 프로토콜."""

    def run(self, args: list[str], cwd: str) -> CommandResult:
        """명령을 실행하고 결과를 반환한다."""
        ...


class SubprocessRunner:
    """subprocess 기반 명령 실행기."""

    def run(self, args: list[str], cwd: str) -> CommandResult:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


class GradleRunner:
    """Gradle 빌드/테스트 실행기."""

    def __init__(self, runner: CommandRunner, project_root: str) -> None:
        self._runner = runner
        self._project_root = project_root

    def build_and_test(self) -> CommandResult:
        """Gradle 빌드 및 테스트를 실행한다."""
        return self._runner.run(
            ["./gradlew", "build", "--no-daemon"],
            cwd=self._project_root,
        )


class GitRunner:
    """Git 명령 실행기."""

    def __init__(self, runner: CommandRunner, project_root: str) -> None:
        self._runner = runner
        self._project_root = project_root

    def create_branch(self, branch_name: str) -> CommandResult:
        """브랜치를 생성하고 체크아웃한다."""
        return self._runner.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self._project_root,
        )

    def checkout(self, branch_name: str) -> CommandResult:
        """기존 브랜치로 체크아웃한다."""
        return self._runner.run(
            ["git", "checkout", branch_name],
            cwd=self._project_root,
        )

    def add_and_commit(self, files: list[str], message: str) -> CommandResult:
        """파일을 스테이징하고 커밋한다."""
        for f in files:
            self._runner.run(["git", "add", f], cwd=self._project_root)
        return self._runner.run(
            ["git", "commit", "-m", message],
            cwd=self._project_root,
        )

    def branch_exists(self, branch_name: str) -> bool:
        """브랜치가 존재하는지 확인한다."""
        result = self._runner.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=self._project_root,
        )
        return result.success
