"""tasks.yaml 생성 로직.

requirements.md를 LLM으로 분석하여 Task 목록을 생성하고,
qa_task_id를 자동 부여한다.
"""

from __future__ import annotations

import yaml

from agentcrew.agents.agent1.llm import LLMProvider
from agentcrew.agents.agent2.prompts.templates import (
    DECOMPOSE_TASKS_PROMPT,
    SYSTEM_PROMPT,
)
from agentcrew.schemas.task import Task, TaskLayer, TaskPriority, TasksFile


async def generate_tasks(llm: LLMProvider, requirements_md: str) -> TasksFile:
    """requirements.md를 분석하여 TasksFile을 생성한다.

    LLM에 requirements.md를 전달하고, 응답을 파싱하여
    Task 목록을 구성한 뒤 qa_task_id를 자동 부여한다.

    Args:
        llm: LLM 프로바이더 인스턴스.
        requirements_md: requirements.md 파일 내용.

    Returns:
        생성된 TasksFile.

    Raises:
        ValueError: requirements_md가 비어 있는 경우.
    """
    if not requirements_md or not requirements_md.strip():
        raise ValueError("requirements.md 내용이 비어 있습니다.")

    prompt = DECOMPOSE_TASKS_PROMPT.format(requirements_md=requirements_md)
    response = await llm.generate(prompt, system=SYSTEM_PROMPT)

    tasks = _parse_tasks_response(response)
    tasks = assign_qa_task_ids(tasks)

    return TasksFile(tasks=tasks)


def _parse_tasks_response(response: str) -> list[Task]:
    """LLM 응답에서 Task 목록을 파싱한다.

    Args:
        response: LLM 응답 텍스트 (YAML 포함).

    Returns:
        파싱된 Task 리스트.
    """
    try:
        if "```yaml" in response:
            yaml_block = response.split("```yaml")[1].split("```")[0]
        elif "```" in response:
            yaml_block = response.split("```")[1].split("```")[0]
        else:
            yaml_block = response

        data = yaml.safe_load(yaml_block)
    except (yaml.YAMLError, IndexError):
        data = {}

    if not isinstance(data, dict):
        data = {}

    tasks: list[Task] = []
    for item in data.get("tasks", []):
        if not isinstance(item, dict):
            continue

        # layer 유효성 검사 및 기본값
        layer_str = item.get("layer", "service")
        try:
            layer = TaskLayer(layer_str)
        except ValueError:
            layer = TaskLayer.SERVICE

        # priority 유효성 검사
        priority_str = item.get("priority", "medium")
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.MEDIUM

        tasks.append(
            Task(
                id=item.get("id", f"TASK-{len(tasks) + 1:03d}"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                layer=layer,
                priority=priority,
                estimated_hours=float(item.get("estimated_hours", 1.0)),
                files_changed=item.get("files_changed", []),
                depends_on=item.get("depends_on", []),
            )
        )

    return tasks


def assign_qa_task_ids(tasks: list[Task]) -> list[Task]:
    """각 구현 Task에 대응하는 QA Task ID를 자동 부여한다.

    test 레이어 작업을 제외한 모든 작업에 QA Task ID를 부여한다.
    QA Task ID 형식: 원본 ID + "-QA" (예: TASK-001 → TASK-001-QA).

    Args:
        tasks: 원본 Task 리스트.

    Returns:
        qa_task_id가 부여된 Task 리스트.
    """
    for task in tasks:
        if task.layer != TaskLayer.TEST and task.qa_task_id is None:
            task.qa_task_id = f"{task.id}-QA"

    return tasks


def render_tasks_yaml(tasks_file: TasksFile) -> str:
    """TasksFile을 YAML 문자열로 렌더링한다.

    Args:
        tasks_file: TasksFile 모델.

    Returns:
        YAML 형식 문자열.
    """
    data = {
        "tasks": [
            task.model_dump(mode="json", exclude_none=False)
            for task in tasks_file.tasks
        ]
    }
    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
