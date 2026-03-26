"""파일 읽기 로직 — progress, tasks, config, logs, history, pipeline trigger."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import yaml

from agentcrew.prm.progress_monitor import ProgressMonitor
from agentcrew.schemas.config import Config
from agentcrew.schemas.progress import Progress
from agentcrew.schemas.task import TasksFile

BASE_DIR = Path(".agentcrew")
PIPELINE_LOGS_DIR = Path("pipeline-logs")


def get_progress() -> Progress:
    monitor = ProgressMonitor(BASE_DIR / "progress.json")
    return monitor.load()


def get_tasks() -> TasksFile:
    tasks_path = BASE_DIR / "tasks.yaml"
    if not tasks_path.exists():
        return TasksFile()
    text = tasks_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    return TasksFile.model_validate(data)


def get_config() -> Config | None:
    for name in ("config.yaml", "config.example.yaml"):
        p = BASE_DIR / name
        if p.exists():
            text = p.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
            return Config.model_validate(data)
    return None


def get_logs() -> list[dict[str, Any]]:
    if not PIPELINE_LOGS_DIR.exists():
        return []
    files = sorted(PIPELINE_LOGS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
    if not files:
        return []
    latest = files[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def get_history() -> list[dict[str, Any]]:
    if not PIPELINE_LOGS_DIR.exists():
        return []
    entries: list[dict[str, Any]] = []
    files = sorted(PIPELINE_LOGS_DIR.glob("*.json"), key=lambda f: f.name)
    for i, f in enumerate(files, 1):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        logs = data if isinstance(data, list) else [data]
        status = "success"
        started_at = None
        ended_at = None
        llm_calls = 0
        for entry in logs:
            if isinstance(entry, dict):
                if entry.get("level") == "error":
                    status = "failed"
                if entry.get("timestamp"):
                    ts = entry["timestamp"]
                    if started_at is None:
                        started_at = ts
                    ended_at = ts
                if entry.get("type") == "llm_call" or "llm" in str(entry.get("message", "")).lower():
                    llm_calls += 1
        entries.append({
            "run_id": i,
            "started_at": started_at,
            "ended_at": ended_at,
            "status": status,
            "llm_calls": llm_calls,
            "log_file": f.name,
        })
    return entries


# ---------------------------------------------------------------------------
# Pipeline trigger
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


class StubLLMProvider:
    """대시보드 트리거용 스텁 LLM. TODO: config에서 실제 provider 생성."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[STUB] LLM response for: {prompt[:50]}..."


async def run_pipeline(input_text: str, **kwargs: Any) -> None:
    """PRMOrchestrator를 생성하여 파이프라인을 실행한다.

    실행 중 상태는 progress.json에 자동 기록된다 (기존 ProgressMonitor).
    성공/실패 모두 로그를 저장한다.
    """
    from agentcrew.prm.progress_monitor import ProgressMonitor

    monitor = ProgressMonitor(BASE_DIR / "progress.json")
    try:
        logger.info("Pipeline started with input: %s", input_text[:80])
        monitor.update(pipeline_status="running", current_agent="orchestrator")

        # TODO: PRMOrchestrator를 실제로 생성하여 실행
        # llm = StubLLMProvider()
        # orchestrator = PRMOrchestrator(llm_provider=llm, ...)
        # await orchestrator.run(input_text, **kwargs)

        # Placeholder: 스텁 실행
        await asyncio.sleep(1)

        monitor.update(pipeline_status="completed", current_agent=None)
        logger.info("Pipeline completed successfully")
    except asyncio.CancelledError:
        monitor.update(pipeline_status="cancelled", current_agent=None)
        logger.warning("Pipeline was cancelled")
        raise
    except Exception as exc:
        monitor.update(pipeline_status="failed", current_agent=None, error=str(exc))
        logger.error("Pipeline failed: %s", exc)
