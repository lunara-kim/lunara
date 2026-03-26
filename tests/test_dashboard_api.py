"""Dashboard API 엔드포인트 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from agentcrew.dashboard.app import app


@pytest.fixture
def setup_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """테스트용 .agentcrew/ 및 pipeline-logs/ 디렉토리 설정."""
    monkeypatch.chdir(tmp_path)
    agentcrew_dir = tmp_path / ".agentcrew"
    agentcrew_dir.mkdir()
    logs_dir = tmp_path / "pipeline-logs"
    logs_dir.mkdir()
    return tmp_path, agentcrew_dir, logs_dir


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_progress_empty(client, setup_dirs):
    res = await client.get("/api/progress")
    assert res.status_code == 200
    data = res.json()
    assert data["pipeline_status"] == "idle"
    assert data["current_agent"] is None


@pytest.mark.asyncio
async def test_progress_with_file(client, setup_dirs):
    _, agentcrew_dir, _ = setup_dirs
    progress = {
        "pipeline_status": "running",
        "current_agent": "agent1",
        "started_at": "2026-03-26T14:00:00Z",
        "updated_at": "2026-03-26T14:05:00Z",
        "error": None,
    }
    (agentcrew_dir / "progress.json").write_text(json.dumps(progress))
    res = await client.get("/api/progress")
    assert res.status_code == 200
    assert res.json()["pipeline_status"] == "running"
    assert res.json()["current_agent"] == "agent1"


@pytest.mark.asyncio
async def test_tasks_empty(client, setup_dirs):
    res = await client.get("/api/tasks")
    assert res.status_code == 200
    assert res.json()["tasks"] == []


@pytest.mark.asyncio
async def test_tasks_with_file(client, setup_dirs):
    _, agentcrew_dir, _ = setup_dirs
    tasks_yaml = "tasks:\n  - id: TASK-001\n    title: Test\n    layer: entity\n"
    (agentcrew_dir / "tasks.yaml").write_text(tasks_yaml)
    res = await client.get("/api/tasks")
    assert res.status_code == 200
    assert len(res.json()["tasks"]) == 1


@pytest.mark.asyncio
async def test_config_empty(client, setup_dirs):
    res = await client.get("/api/config")
    assert res.status_code == 200
    assert res.json() == {}


@pytest.mark.asyncio
async def test_logs_empty(client, setup_dirs):
    res = await client.get("/api/logs")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_logs_with_file(client, setup_dirs):
    _, _, logs_dir = setup_dirs
    log_data = [{"timestamp": "15:00:00", "agent": "agent1", "level": "info", "message": "test"}]
    (logs_dir / "run-001.json").write_text(json.dumps(log_data))
    res = await client.get("/api/logs")
    assert res.status_code == 200
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_history_empty(client, setup_dirs):
    res = await client.get("/api/history")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_pipeline_run(client, setup_dirs):
    res = await client.post("/api/pipeline/run", json={"input_text": "테스트 요구사항"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    assert "시작" in data["message"]


@pytest.mark.asyncio
async def test_pipeline_status(client, setup_dirs):
    res = await client.get("/api/pipeline/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_running" in data


@pytest.mark.asyncio
async def test_pipeline_cancel_no_task(client, setup_dirs):
    # Reset state
    app.state.running_task = None
    res = await client.post("/api/pipeline/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "error"


@pytest.mark.asyncio
async def test_pipeline_duplicate_run(client, setup_dirs):
    import asyncio

    # Start a long-running fake task
    async def slow():
        await asyncio.sleep(60)

    app.state.running_task = asyncio.create_task(slow())
    try:
        res = await client.post("/api/pipeline/run", json={"input_text": "중복 실행"})
        assert res.status_code == 200
        assert res.json()["status"] == "error"
    finally:
        app.state.running_task.cancel()
        try:
            await app.state.running_task
        except asyncio.CancelledError:
            pass
        app.state.running_task = None


@pytest.mark.asyncio
async def test_history_with_files(client, setup_dirs):
    _, _, logs_dir = setup_dirs
    for i in range(3):
        data = [{"timestamp": f"15:0{i}:00", "level": "info", "message": "ok"}]
        (logs_dir / f"run-{i:03d}.json").write_text(json.dumps(data))
    res = await client.get("/api/history")
    assert res.status_code == 200
    assert len(res.json()) == 3
