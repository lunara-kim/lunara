"""curl 스모크 테스트 실행기.

LLM이 생성한 curl 시나리오를 실행하고 기대값과 대조한다.
CommandRunner Protocol을 사용하여 테스트 가능하게 구현.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from agentcrew.agents.agent3.executor import CommandRunner, CommandResult


@dataclass
class CurlScenario:
    """curl 테스트 시나리오."""

    name: str
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    expected_status: int = 200
    expected_body_contains: list[str] = field(default_factory=list)
    auth_required: bool = False


@dataclass
class CurlTestResult:
    """curl 테스트 개별 결과."""

    scenario_name: str
    passed: bool
    actual_status: int = 0
    actual_body: str = ""
    error_message: str = ""
    missing_keywords: list[str] = field(default_factory=list)


@dataclass
class CurlTestSummary:
    """curl 테스트 전체 요약."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[CurlTestResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.total > 0


def parse_scenarios(json_text: str) -> list[CurlScenario]:
    """LLM 응답의 JSON을 CurlScenario 목록으로 파싱한다.

    Args:
        json_text: JSON 배열 문자열.

    Returns:
        CurlScenario 목록.
    """
    # JSON 코드 블록 제거
    text = json_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄과 마지막 줄(```) 제거
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    scenarios: list[CurlScenario] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        scenarios.append(
            CurlScenario(
                name=item.get("name", "unnamed"),
                method=item.get("method", "GET"),
                url=item.get("url", ""),
                headers=item.get("headers", {}),
                body=item.get("body"),
                expected_status=item.get("expected_status", 200),
                expected_body_contains=item.get("expected_body_contains", []),
                auth_required=item.get("auth_required", False),
            )
        )
    return scenarios


def build_curl_args(scenario: CurlScenario) -> list[str]:
    """CurlScenario를 curl 명령 인자 목록으로 변환한다.

    Args:
        scenario: curl 시나리오.

    Returns:
        curl 명령 인자 리스트.
    """
    args = [
        "curl", "-s", "-o", "/dev/null",
        "-w", "%{http_code}\n%{stdout}",
        "-X", scenario.method,
    ]

    for key, value in scenario.headers.items():
        args.extend(["-H", f"{key}: {value}"])

    if scenario.body is not None:
        body_str = scenario.body if isinstance(scenario.body, str) else json.dumps(scenario.body)
        args.extend(["-d", body_str])

    args.append(scenario.url)
    return args


def build_curl_args_with_body(scenario: CurlScenario) -> list[str]:
    """응답 본문을 캡처하는 curl 명령 인자 목록을 생성한다.

    Args:
        scenario: curl 시나리오.

    Returns:
        curl 명령 인자 리스트.
    """
    args = [
        "curl", "-s",
        "-w", "\n__HTTP_STATUS__%{http_code}",
        "-X", scenario.method,
    ]

    for key, value in scenario.headers.items():
        args.extend(["-H", f"{key}: {value}"])

    if scenario.body is not None:
        body_str = scenario.body if isinstance(scenario.body, str) else json.dumps(scenario.body)
        args.extend(["-d", body_str])

    args.append(scenario.url)
    return args


def inject_auth_header(
    scenario: CurlScenario, token: str
) -> CurlScenario:
    """인증 토큰을 시나리오 헤더에 주입한다.

    Args:
        scenario: 원본 시나리오.
        token: Bearer 토큰.

    Returns:
        인증 헤더가 추가된 새 시나리오.
    """
    new_headers = {**scenario.headers, "Authorization": f"Bearer {token}"}
    return CurlScenario(
        name=scenario.name,
        method=scenario.method,
        url=scenario.url,
        headers=new_headers,
        body=scenario.body,
        expected_status=scenario.expected_status,
        expected_body_contains=scenario.expected_body_contains,
        auth_required=scenario.auth_required,
    )


def run_curl_scenario(
    runner: CommandRunner, scenario: CurlScenario, cwd: str
) -> CurlTestResult:
    """단일 curl 시나리오를 실행하고 결과를 반환한다.

    Args:
        runner: 명령 실행기.
        scenario: curl 시나리오.
        cwd: 작업 디렉토리.

    Returns:
        테스트 결과.
    """
    args = build_curl_args_with_body(scenario)

    try:
        result: CommandResult = runner.run(args, cwd)
    except Exception as e:
        return CurlTestResult(
            scenario_name=scenario.name,
            passed=False,
            error_message=f"curl 실행 실패: {e}",
        )

    # HTTP 상태코드와 본문 분리
    output = result.stdout
    actual_status = 0
    actual_body = ""

    if "__HTTP_STATUS__" in output:
        parts = output.rsplit("__HTTP_STATUS__", 1)
        actual_body = parts[0].strip()
        try:
            actual_status = int(parts[1].strip())
        except (ValueError, IndexError):
            actual_status = 0
    else:
        actual_body = output

    # 상태코드 검증
    status_ok = actual_status == scenario.expected_status

    # 본문 키워드 검증
    missing_keywords: list[str] = []
    for keyword in scenario.expected_body_contains:
        if keyword not in actual_body:
            missing_keywords.append(keyword)

    passed = status_ok and len(missing_keywords) == 0

    error_msg = ""
    if not status_ok:
        error_msg = f"기대 상태: {scenario.expected_status}, 실제: {actual_status}"
    if missing_keywords:
        if error_msg:
            error_msg += "; "
        error_msg += f"누락 키워드: {missing_keywords}"

    return CurlTestResult(
        scenario_name=scenario.name,
        passed=passed,
        actual_status=actual_status,
        actual_body=actual_body[:2000],  # 2KB 제한
        error_message=error_msg,
        missing_keywords=missing_keywords,
    )


def run_all_scenarios(
    runner: CommandRunner,
    scenarios: list[CurlScenario],
    cwd: str,
    *,
    auth_token: str | None = None,
) -> CurlTestSummary:
    """모든 curl 시나리오를 실행하고 요약을 반환한다.

    Args:
        runner: 명령 실행기.
        scenarios: curl 시나리오 목록.
        cwd: 작업 디렉토리.
        auth_token: 인증 토큰 (있으면 auth_required 시나리오에 주입).

    Returns:
        테스트 요약.
    """
    results: list[CurlTestResult] = []

    for scenario in scenarios:
        if scenario.auth_required and auth_token:
            scenario = inject_auth_header(scenario, auth_token)

        result = run_curl_scenario(runner, scenario, cwd)
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    return CurlTestSummary(
        total=len(results),
        passed=passed,
        failed=failed,
        results=results,
    )
