"""Gradle test 실행 및 결과 파싱.

GradleRunner를 통해 테스트를 실행하고 결과를 구조화한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agentcrew.agents.agent3.executor import CommandRunner, GradleRunner


@dataclass
class GradleTestResult:
    """Gradle 테스트 실행 결과."""

    success: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error_output: str = ""
    raw_stdout: str = ""
    raw_stderr: str = ""
    failed_tests: list[str] = field(default_factory=list)


def run_gradle_tests(runner: CommandRunner, project_root: str) -> GradleTestResult:
    """Gradle 테스트를 실행하고 결과를 파싱한다.

    Args:
        runner: 명령 실행기.
        project_root: 프로젝트 루트 경로.

    Returns:
        파싱된 테스트 결과.
    """
    gradle = GradleRunner(runner, project_root)
    result = gradle.build_and_test()
    return parse_gradle_output(
        result.stdout, result.stderr, result.success
    )


def parse_gradle_output(
    stdout: str, stderr: str, success: bool
) -> GradleTestResult:
    """Gradle 출력을 파싱하여 GradleTestResult를 반환한다.

    Args:
        stdout: 표준 출력.
        stderr: 표준 에러.
        success: 명령 성공 여부.

    Returns:
        파싱된 테스트 결과.
    """
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    failed_tests: list[str] = []
    combined = stdout + "\n" + stderr

    # Gradle 테스트 요약 파싱: "X tests completed, Y failed, Z skipped"
    # 또는 "X tests completed, Y failed"
    summary_pattern = re.compile(
        r"(\d+)\s+tests?\s+completed"
        r"(?:,\s*(\d+)\s+failed)?"
        r"(?:,\s*(\d+)\s+skipped)?",
    )
    for match in summary_pattern.finditer(combined):
        t = int(match.group(1))
        f = int(match.group(2)) if match.group(2) else 0
        s = int(match.group(3)) if match.group(3) else 0
        total += t
        failed += f
        skipped += s

    passed = total - failed - skipped

    # 실패한 테스트명 추출
    fail_pattern = re.compile(r"(\S+)\s+>\s+(\S+).*FAILED")
    for match in fail_pattern.finditer(combined):
        failed_tests.append(f"{match.group(1)}.{match.group(2)}")

    error_output = ""
    if not success:
        # 마지막 3000자를 에러 출력으로
        error_output = combined[-3000:]

    return GradleTestResult(
        success=success,
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        error_output=error_output,
        raw_stdout=stdout,
        raw_stderr=stderr,
        failed_tests=failed_tests,
    )
