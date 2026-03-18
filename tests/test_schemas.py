"""스키마 기본 테스트."""

from datetime import datetime, timezone

from agentcrew.schemas import (
    Config,
    PipelineStatus,
    Progress,
    ProgressError,
    RepoConfig,
    Task,
    TaskLayer,
    TaskPriority,
    TasksFile,
    TaskStatus,
)


class TestProgress:
    """Progress 스키마 테스트."""

    def test_default_progress(self) -> None:
        progress = Progress()
        assert progress.pipeline_status == PipelineStatus.IDLE
        assert progress.current_agent is None
        assert progress.error is None

    def test_running_progress(self) -> None:
        now = datetime.now(tz=timezone.utc)
        progress = Progress(
            pipeline_status=PipelineStatus.RUNNING,
            current_agent="agent1",
            started_at=now,
            updated_at=now,
        )
        assert progress.pipeline_status == PipelineStatus.RUNNING
        assert progress.current_agent == "agent1"

    def test_progress_with_error(self) -> None:
        now = datetime.now(tz=timezone.utc)
        error = ProgressError(
            agent="agent3",
            message="Build failed",
            timestamp=now,
            retry_count=2,
        )
        progress = Progress(
            pipeline_status=PipelineStatus.FAILED,
            error=error,
        )
        assert progress.error is not None
        assert progress.error.agent == "agent3"
        assert progress.error.retry_count == 2


class TestTask:
    """Task 스키마 테스트."""

    def test_minimal_task(self) -> None:
        task = Task(id="TASK-001", title="엔티티 생성", layer=TaskLayer.ENTITY)
        assert task.status == TaskStatus.NEW
        assert task.priority == TaskPriority.MEDIUM
        assert task.files_changed == []
        assert task.depends_on == []

    def test_full_task(self) -> None:
        task = Task(
            id="TASK-002",
            title="서비스 구현",
            description="UserService 구현",
            layer=TaskLayer.SERVICE,
            priority=TaskPriority.HIGH,
            estimated_hours=2.5,
            status=TaskStatus.IN_PROGRESS,
            files_changed=["src/main/java/UserService.java"],
            qa_task_id="TASK-QA-002",
            depends_on=["TASK-001"],
        )
        assert task.estimated_hours == 2.5
        assert len(task.files_changed) == 1

    def test_tasks_file(self) -> None:
        tasks_file = TasksFile(
            tasks=[
                Task(id="TASK-001", title="테스트", layer=TaskLayer.TEST),
            ]
        )
        assert len(tasks_file.tasks) == 1


class TestConfig:
    """Config 스키마 테스트."""

    def test_minimal_config(self) -> None:
        config = Config(repo=RepoConfig(url="https://github.com/example/repo.git"))
        assert config.repo.branch == "main"
        assert config.default_model.model == "gpt-4o"
        assert config.agents.agent1.enabled is True
        assert config.notification.enabled is False
