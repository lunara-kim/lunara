"""qa-report.md 생성 로직.

Gradle 테스트 결과와 curl 스모크 테스트 결과를 종합하여
Pass/Fail 목록이 포함된 QA 보고서를 생성한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agentcrew.agents.agent4.curl_runner import CurlTestSummary
from agentcrew.agents.agent4.gradle_parser import GradleTestResult


def generate_qa_report(
    task_id: str,
    gradle_result: GradleTestResult,
    curl_summary: CurlTestSummary | None,
) -> str:
    """QA 보고서 마크다운 문자열을 생성한다.

    Args:
        task_id: 대상 Task ID.
        gradle_result: Gradle 테스트 결과.
        curl_summary: curl 스모크 테스트 요약 (없으면 None).

    Returns:
        마크다운 형식의 QA 보고서.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    gradle_ok = gradle_result.success
    curl_ok = curl_summary is None or curl_summary.success
    overall = "PASS" if (gradle_ok and curl_ok) else "FAIL"

    lines: list[str] = []
    lines.append(f"# QA Report — {task_id}")
    lines.append(f"")
    lines.append(f"- **Date:** {now}")
    lines.append(f"- **Overall Verdict:** {overall}")
    lines.append(f"")

    # Gradle 섹션
    lines.append(f"## Gradle Test Results")
    lines.append(f"")
    lines.append(f"- **Status:** {'PASS' if gradle_ok else 'FAIL'}")
    lines.append(f"- **Total:** {gradle_result.total}")
    lines.append(f"- **Passed:** {gradle_result.passed}")
    lines.append(f"- **Failed:** {gradle_result.failed}")
    lines.append(f"- **Skipped:** {gradle_result.skipped}")
    lines.append(f"")

    if gradle_result.failed_tests:
        lines.append(f"### Failed Tests")
        lines.append(f"")
        for test_name in gradle_result.failed_tests:
            lines.append(f"- ❌ `{test_name}`")
        lines.append(f"")

    if gradle_result.error_output:
        lines.append(f"### Error Output")
        lines.append(f"")
        lines.append(f"```")
        lines.append(gradle_result.error_output[:2000])
        lines.append(f"```")
        lines.append(f"")

    # Curl 섹션
    lines.append(f"## Curl Smoke Test Results")
    lines.append(f"")
    if curl_summary is None or curl_summary.total == 0:
        lines.append(f"_No curl smoke tests applicable for this task._")
    else:
        lines.append(f"- **Total:** {curl_summary.total}")
        lines.append(f"- **Passed:** {curl_summary.passed}")
        lines.append(f"- **Failed:** {curl_summary.failed}")
        lines.append(f"")
        lines.append(f"### Scenario Details")
        lines.append(f"")
        for r in curl_summary.results:
            icon = "✅" if r.passed else "❌"
            lines.append(f"- {icon} **{r.scenario_name}** — HTTP {r.actual_status}")
            if r.error_message:
                lines.append(f"  - {r.error_message}")
        lines.append(f"")

    return "\n".join(lines)


def save_qa_report(
    report_content: str,
    output_path: str,
) -> None:
    """QA 보고서를 파일에 저장한다.

    Args:
        report_content: 마크다운 보고서 내용.
        output_path: 저장 경로.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report_content, encoding="utf-8")


def is_qa_passed(
    gradle_result: GradleTestResult,
    curl_summary: CurlTestSummary | None,
) -> bool:
    """QA 전체 통과 여부를 반환한다.

    Args:
        gradle_result: Gradle 테스트 결과.
        curl_summary: curl 스모크 테스트 요약.

    Returns:
        전체 PASS이면 True.
    """
    gradle_ok = gradle_result.success
    curl_ok = curl_summary is None or curl_summary.success
    return gradle_ok and curl_ok
