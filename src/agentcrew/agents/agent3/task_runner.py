"""tasks.yaml 상태 갱신 및 progress.json 관리.

Task 상태를 new → in_progress → resolved로 전이하고,
빌드 실패 시 progress.json에 에러를 기록한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from agentcrew.schemas.progress import Progress, ProgressError
from agentcrew.schemas.task import Task, TasksFile, TaskStatus


def load_tasks_yaml(path: str) -> TasksFile:
    """tasks.yaml을 로드한다."""
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    if data is None:
        return TasksFile(tasks=[])
    return TasksFile(**data)


def save_tasks_yaml(path: str, tasks_file: TasksFile) -> None:
    """tasks.yaml을 저장한다."""
    data = tasks_file.model_dump(mode="json")
    Path(path).write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def update_task_status(tasks_file: TasksFile, task_id: str, status: TaskStatus) -> TasksFile:
    """특정 Task의 상태를 갱신하여 새 TasksFile을 반환한다."""
    updated_tasks: list[Task] = []
    for task in tasks_file.tasks:
        if task.id == task_id:
            updated = task.model_copy(update={"status": status})
            updated_tasks.append(updated)
        else:
            updated_tasks.append(task)
    return TasksFile(tasks=updated_tasks)


def load_progress(path: str) -> Progress:
    """progress.json을 로드한다."""
    p = Path(path)
    if not p.exists():
        return Progress()
    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    return Progress(**data)


def save_progress(path: str, progress: Progress) -> None:
    """progress.json을 저장한다."""
    import json
    data = progress.model_dump(mode="json")
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def record_build_error(
    progress: Progress,
    task_id: str,
    error_message: str,
    retry_count: int,
) -> Progress:
    """빌드 실패 에러를 progress.json에 기록한다."""
    error = ProgressError(
        agent="agent3",
        message=f"Task {task_id}: {error_message}",
        timestamp=datetime.now(timezone.utc),
        retry_count=retry_count,
    )
    return progress.model_copy(update={"error": error})


def get_pending_tasks(tasks_file: TasksFile) -> list[Task]:
    """status가 new인 Task들을 우선순위 순으로 반환한다."""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    pending = [t for t in tasks_file.tasks if t.status == TaskStatus.NEW]
    return sorted(pending, key=lambda t: priority_order.get(t.priority, 1))
