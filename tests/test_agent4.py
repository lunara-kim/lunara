"""Agent 4 QA 검증 에이전트 유닛테스트."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agentcrew.agents.agent3.executor import CommandResult
from agentcrew.agents.agent4.agent import PipelineAbortError, QAVerificationAgent
from agentcrew.agents.agent4.auth import fetch_auth_token
from agentcrew.agents.agent4.curl_runner import (
    CurlScenario,
    CurlTestResult,
    CurlTestSummary,
    build_curl_args_with_body,
    inject_auth_header,
    parse_scenarios,
    run_all_scenarios,
    run_curl_scenario,
)
from agentcrew.agents.agent4.gradle_parser import (
    GradleTestResult,
    parse_gradle_output,
)
from agentcrew.agents.agent4.report import (
    generate_qa_report,
    is_qa_passed,
    save_qa_report,
)


# ── Fake 구현체 ──────────────────────────────────────────────


class FakeRunner:
    """테스트용 CommandRunner."""

    def __init__(self, results: list[CommandResult] | None = None):
        self._results = list(results) if results else []
        self._call_index = 0
        self.calls: list[tuple[list[str], str]] = []

    def run(self, args: list[str], cwd: str) -> CommandResult:
        self.calls.append((args, cwd))
        if self._call_index < len(self._results):
            result = self._results[self._call_index]
            self._call_index += 1
            return result
        return CommandResult(returncode=0, stdout="", stderr="")


class FakeLLM:
    """테스트용 LLMProvider."""

    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses) if responses else []
        self._call_index = 0

    async def generate(self, prompt: str, *, system: str = "") -> str:
        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
            self._call_index += 1
            return resp
        return ""


class FakeFS:
    """테스트용 FileSystemProvider."""

    def __init__(self, files: dict[str, str] | None = None):
        self._files = dict(files) if files else {}

    def read_file(self, path: str) -> str:
        return self._files.get(path, "")

    def write_file(self, path: str, content: str) -> None:
        self._files[path] = content

    def list_tree(self, root: str, max_depth: int = 3) -> str:
        return "src/\n  main/"

    def exists(self, path: str) -> bool:
        return path in self._files


# ── Gradle Parser Tests ──────────────────────────────────────


class TestGradleParser:
    def test_parse_success(self):
        stdout = "BUILD SUCCESSFUL\n10 tests completed, 0 failed"
        result = parse_gradle_output(stdout, "", True)
        assert result.success is True
        assert result.total == 10
        assert result.passed == 10
        assert result.failed == 0

    def test_parse_failure(self):
        stdout = "5 tests completed, 2 failed, 1 skipped"
        result = parse_gradle_output(stdout, "", False)
        assert result.success is False
        assert result.total == 5
        assert result.failed == 2
        assert result.skipped == 1
        assert result.passed == 2

    def test_parse_failed_test_names(self):
        stdout = textwrap.dedent("""\
            UserServiceTest > createUser FAILED
            OrderServiceTest > placeOrder FAILED
            10 tests completed, 2 failed
        """)
        result = parse_gradle_output(stdout, "", False)
        assert "UserServiceTest.createUser" in result.failed_tests
        assert "OrderServiceTest.placeOrder" in result.failed_tests

    def test_parse_no_tests(self):
        result = parse_gradle_output("BUILD SUCCESSFUL", "", True)
        assert result.success is True
        assert result.total == 0

    def test_error_output_truncated(self):
        long_error = "x" * 5000
        result = parse_gradle_output(long_error, "", False)
        assert len(result.error_output) == 3000


# ── Curl Runner Tests ────────────────────────────────────────


class TestCurlScenarioParsing:
    def test_parse_valid_json(self):
        json_text = json.dumps([
            {
                "name": "Get users",
                "method": "GET",
                "url": "http://localhost:8080/api/users",
                "expected_status": 200,
                "expected_body_contains": ["id"],
                "auth_required": False,
            }
        ])
        scenarios = parse_scenarios(json_text)
        assert len(scenarios) == 1
        assert scenarios[0].name == "Get users"
        assert scenarios[0].method == "GET"

    def test_parse_with_code_block(self):
        text = '```json\n[{"name":"test","method":"GET","url":"http://x"}]\n```'
        scenarios = parse_scenarios(text)
        assert len(scenarios) == 1

    def test_parse_invalid_json(self):
        assert parse_scenarios("not json") == []

    def test_parse_empty_array(self):
        assert parse_scenarios("[]") == []


class TestCurlExecution:
    def test_run_curl_success(self):
        runner = FakeRunner([
            CommandResult(
                returncode=0,
                stdout='{"id":1}\n__HTTP_STATUS__200',
                stderr="",
            )
        ])
        scenario = CurlScenario(
            name="test",
            method="GET",
            url="http://localhost:8080/api/test",
            expected_status=200,
            expected_body_contains=["id"],
        )
        result = run_curl_scenario(runner, scenario, "/tmp")
        assert result.passed is True
        assert result.actual_status == 200

    def test_run_curl_status_mismatch(self):
        runner = FakeRunner([
            CommandResult(returncode=0, stdout="error\n__HTTP_STATUS__404", stderr="")
        ])
        scenario = CurlScenario(
            name="test", method="GET", url="http://x", expected_status=200
        )
        result = run_curl_scenario(runner, scenario, "/tmp")
        assert result.passed is False
        assert result.actual_status == 404

    def test_run_curl_missing_keyword(self):
        runner = FakeRunner([
            CommandResult(returncode=0, stdout='{"name":"a"}\n__HTTP_STATUS__200', stderr="")
        ])
        scenario = CurlScenario(
            name="test",
            method="GET",
            url="http://x",
            expected_status=200,
            expected_body_contains=["missing_key"],
        )
        result = run_curl_scenario(runner, scenario, "/tmp")
        assert result.passed is False
        assert "missing_key" in result.missing_keywords

    def test_run_all_scenarios(self):
        runner = FakeRunner([
            CommandResult(returncode=0, stdout='ok\n__HTTP_STATUS__200', stderr=""),
            CommandResult(returncode=0, stdout='fail\n__HTTP_STATUS__500', stderr=""),
        ])
        scenarios = [
            CurlScenario(name="s1", method="GET", url="http://x", expected_status=200),
            CurlScenario(name="s2", method="GET", url="http://x", expected_status=200),
        ]
        summary = run_all_scenarios(runner, scenarios, "/tmp")
        assert summary.total == 2
        assert summary.passed == 1
        assert summary.failed == 1


class TestCurlAuthInjection:
    def test_inject_auth_header(self):
        scenario = CurlScenario(
            name="test", method="GET", url="http://x",
            headers={"Content-Type": "application/json"},
            auth_required=True,
        )
        new_scenario = inject_auth_header(scenario, "my-token")
        assert new_scenario.headers["Authorization"] == "Bearer my-token"
        assert new_scenario.headers["Content-Type"] == "application/json"

    def test_build_curl_args_with_body(self):
        scenario = CurlScenario(
            name="test", method="POST", url="http://x",
            headers={"Content-Type": "application/json"},
            body='{"key":"val"}',
        )
        args = build_curl_args_with_body(scenario)
        assert "curl" in args
        assert "-X" in args
        assert "POST" in args
        assert "-d" in args


# ── Auth Tests ───────────────────────────────────────────────


class TestAuth:
    def test_fetch_token_success(self):
        runner = FakeRunner([
            CommandResult(
                returncode=0,
                stdout='{"token":"abc123"}',
                stderr="",
            )
        ])
        token = fetch_auth_token(runner, "/tmp")
        assert token == "abc123"

    def test_fetch_token_access_token_field(self):
        runner = FakeRunner([
            CommandResult(
                returncode=0,
                stdout='{"access_token":"xyz"}',
                stderr="",
            )
        ])
        token = fetch_auth_token(runner, "/tmp")
        assert token == "xyz"

    def test_fetch_token_failure(self):
        runner = FakeRunner([
            CommandResult(returncode=7, stdout="", stderr="Connection refused")
        ])
        token = fetch_auth_token(runner, "/tmp")
        assert token is None

    def test_fetch_token_invalid_json(self):
        runner = FakeRunner([
            CommandResult(returncode=0, stdout="not json", stderr="")
        ])
        token = fetch_auth_token(runner, "/tmp")
        assert token is None


# ── Report Tests ─────────────────────────────────────────────


class TestReport:
    def test_generate_report_pass(self):
        gradle = GradleTestResult(success=True, total=5, passed=5, failed=0)
        report = generate_qa_report("TASK-001", gradle, None)
        assert "PASS" in report
        assert "TASK-001" in report

    def test_generate_report_fail(self):
        gradle = GradleTestResult(
            success=False, total=5, passed=3, failed=2,
            failed_tests=["TestA.testB"],
            error_output="compilation error",
        )
        curl = CurlTestSummary(
            total=2, passed=1, failed=1,
            results=[
                CurlTestResult(scenario_name="s1", passed=True, actual_status=200),
                CurlTestResult(
                    scenario_name="s2", passed=False, actual_status=500,
                    error_message="기대 상태: 200, 실제: 500",
                ),
            ],
        )
        report = generate_qa_report("TASK-002", gradle, curl)
        assert "FAIL" in report
        assert "TestA.testB" in report
        assert "s2" in report

    def test_is_qa_passed_true(self):
        gradle = GradleTestResult(success=True, total=1, passed=1, failed=0)
        assert is_qa_passed(gradle, None) is True

    def test_is_qa_passed_false_gradle(self):
        gradle = GradleTestResult(success=False, total=1, passed=0, failed=1)
        assert is_qa_passed(gradle, None) is False

    def test_is_qa_passed_false_curl(self):
        gradle = GradleTestResult(success=True, total=1, passed=1, failed=0)
        curl = CurlTestSummary(total=1, passed=0, failed=1, results=[])
        assert is_qa_passed(gradle, curl) is False

    def test_save_qa_report(self, tmp_path):
        report_path = str(tmp_path / "reports" / "test-report.md")
        save_qa_report("# Test Report", report_path)
        assert Path(report_path).read_text() == "# Test Report"


# ── Agent Integration Tests ──────────────────────────────────


class TestQAVerificationAgent:
    @pytest.fixture
    def tasks_yaml(self, tmp_path):
        """resolved 상태의 Task가 포함된 tasks.yaml."""
        content = textwrap.dedent("""\
            tasks:
              - id: TASK-001
                title: Create User entity
                description: JPA entity
                layer: entity
                status: resolved
                files_changed:
                  - src/main/java/User.java
        """)
        path = tmp_path / "tasks.yaml"
        path.write_text(content)
        return str(path)

    @pytest.mark.asyncio
    async def test_qa_pass(self, tasks_yaml, tmp_path):
        """Gradle 통과 + curl 생략 → qa_pass."""
        llm = FakeLLM()
        fs = FakeFS()
        runner = FakeRunner()

        agent = QAVerificationAgent(
            llm=llm,
            project_root=str(tmp_path),
            fs=fs,
            runner=runner,
        )
        results = await agent.run(
            tasks_yaml,
            skip_gradle=True,
            skip_curl=True,
            report_dir="qa-reports",
        )
        assert results["TASK-001"] == "qa_pass"

        # tasks.yaml 상태 확인
        import yaml
        data = yaml.safe_load(Path(tasks_yaml).read_text())
        assert data["tasks"][0]["status"] == "qa_pass"

    @pytest.mark.asyncio
    async def test_qa_fail_rework_then_pass(self, tasks_yaml, tmp_path):
        """1회 실패 후 재작업으로 통과."""
        # 1차: gradle 실패, 2차: gradle 성공
        runner = FakeRunner([
            # 1차 gradle 실패
            CommandResult(returncode=1, stdout="1 test completed, 1 failed", stderr="error"),
            # 재작업 후 2차 gradle 성공
            CommandResult(returncode=0, stdout="1 test completed, 0 failed", stderr=""),
        ])

        # LLM: 재작업 응답
        llm = FakeLLM([
            '===FILE: src/main/java/User.java===\npublic class User {}\n===END_FILE===',
        ])
        fs = FakeFS()

        agent = QAVerificationAgent(
            llm=llm,
            project_root=str(tmp_path),
            max_rework=2,
            fs=fs,
            runner=runner,
        )
        results = await agent.run(
            tasks_yaml,
            skip_curl=True,
            report_dir="qa-reports",
        )
        assert results["TASK-001"] == "qa_pass"

    @pytest.mark.asyncio
    async def test_qa_fail_pipeline_abort(self, tasks_yaml, tmp_path):
        """재작업 2회 초과 → PipelineAbortError."""
        # 3번 모두 gradle 실패
        runner = FakeRunner([
            CommandResult(returncode=1, stdout="1 test completed, 1 failed", stderr="e1"),
            CommandResult(returncode=1, stdout="1 test completed, 1 failed", stderr="e2"),
            CommandResult(returncode=1, stdout="1 test completed, 1 failed", stderr="e3"),
        ])

        llm = FakeLLM([
            '===FILE: src/main/java/User.java===\nfix1\n===END_FILE===',
            '===FILE: src/main/java/User.java===\nfix2\n===END_FILE===',
        ])
        fs = FakeFS()

        agent = QAVerificationAgent(
            llm=llm,
            project_root=str(tmp_path),
            max_rework=2,
            fs=fs,
            runner=runner,
        )

        with pytest.raises(PipelineAbortError, match="재작업 2회 초과"):
            await agent.run(
                tasks_yaml,
                skip_curl=True,
                report_dir="qa-reports",
            )

        # tasks.yaml에 qa_fail 상태가 기록되어야 함
        import yaml
        data = yaml.safe_load(Path(tasks_yaml).read_text())
        assert data["tasks"][0]["status"] == "qa_fail"

    @pytest.mark.asyncio
    async def test_qa_with_curl_scenarios(self, tasks_yaml, tmp_path):
        """curl 시나리오 생성 및 실행 통합 테스트."""
        scenarios_json = json.dumps([
            {
                "name": "Get user",
                "method": "GET",
                "url": "http://localhost:8080/api/users/1",
                "expected_status": 200,
                "expected_body_contains": ["id"],
                "auth_required": False,
            }
        ])

        runner = FakeRunner([
            # gradle 성공
            CommandResult(returncode=0, stdout="1 test completed", stderr=""),
            # curl 성공
            CommandResult(
                returncode=0,
                stdout='{"id":1}\n__HTTP_STATUS__200',
                stderr="",
            ),
        ])

        llm = FakeLLM([scenarios_json])
        fs = FakeFS({
            f"{tmp_path}/src/main/java/User.java": "public class User {}",
        })

        agent = QAVerificationAgent(
            llm=llm,
            project_root=str(tmp_path),
            fs=fs,
            runner=runner,
        )
        results = await agent.run(
            tasks_yaml,
            report_dir="qa-reports",
        )
        assert results["TASK-001"] == "qa_pass"

    @pytest.mark.asyncio
    async def test_no_resolved_tasks(self, tmp_path):
        """resolved Task가 없으면 빈 결과."""
        content = textwrap.dedent("""\
            tasks:
              - id: TASK-001
                title: test
                layer: entity
                status: new
        """)
        path = tmp_path / "tasks.yaml"
        path.write_text(content)

        agent = QAVerificationAgent(
            llm=FakeLLM(),
            project_root=str(tmp_path),
            fs=FakeFS(),
            runner=FakeRunner(),
        )
        results = await agent.run(str(path), skip_gradle=True, skip_curl=True)
        assert results == {}
