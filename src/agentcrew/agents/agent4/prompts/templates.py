"""Agent 4 QA 검증 프롬프트 템플릿.

curl 스모크 테스트 시나리오 생성 및 QA 보고서 작성용.
"""

SYSTEM_PROMPT = """\
You are a senior QA engineer. You verify implemented code quality through
automated tests and smoke tests. You output structured test scenarios and reports.
"""

GENERATE_CURL_TESTS_PROMPT = """\
## Task Under QA
- ID: {task_id}
- Title: {task_title}
- Description: {task_description}
- Layer: {task_layer}
- Files changed: {files_changed}

## Project Context

### Endpoint Definitions
{endpoint_definitions}

## Instructions
Generate curl smoke test scenarios for the endpoints related to this task.
Each scenario must be in this exact JSON format (output a JSON array):

```json
[
  {{
    "name": "scenario name",
    "method": "GET|POST|PUT|DELETE",
    "url": "http://localhost:8080/api/...",
    "headers": {{"Content-Type": "application/json"}},
    "body": null,
    "expected_status": 200,
    "expected_body_contains": ["keyword1", "keyword2"],
    "auth_required": false
  }}
]
```

Only output the JSON array. No explanations.
If the task layer is not controller/config, output an empty array `[]`.
"""

QA_REPORT_PROMPT = """\
## QA Results Summary

### Gradle Test Results
- Status: {gradle_status}
- Total: {gradle_total}
- Passed: {gradle_passed}
- Failed: {gradle_failed}
- Error output (if any):
```
{gradle_error_output}
```

### Curl Smoke Test Results
{curl_results_summary}

## Instructions
Based on the results above, generate a QA report in markdown format.
Include:
1. Overall verdict: PASS or FAIL
2. Gradle test summary
3. Curl smoke test details (each scenario with pass/fail)
4. Failure details if any
5. Recommendations

Output ONLY the markdown report.
"""

REWORK_REQUEST_PROMPT = """\
## QA Failure Report
The following QA checks failed for task {task_id}:

### Failures
{failure_details}

### Current Files
{current_files}

## Instructions
Fix the code to resolve the QA failures listed above.
Output the corrected files in the same format:

===FILE: path/to/File.java===
<corrected file contents>
===END_FILE===
"""
