"""FastAPI 앱 + 라우트 정의."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agentcrew.dashboard.services import (
    get_config,
    get_history,
    get_logs,
    get_progress,
    get_tasks,
    run_pipeline,
)


class PipelineRunRequest(BaseModel):
    input_text: str
    skip_build: bool = False
    skip_git: bool = False
    skip_gradle: bool = False
    skip_curl: bool = False


app = FastAPI(title="AgentCrew Dashboard API", version="0.1.0")
app.state.running_task: asyncio.Task | None = None  # type: ignore[assignment]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/progress")
def api_progress():
    return get_progress().model_dump(mode="json")


@app.get("/api/tasks")
def api_tasks():
    return get_tasks().model_dump(mode="json")


@app.get("/api/config")
def api_config():
    config = get_config()
    if config is None:
        return {}
    return config.model_dump(mode="json")


@app.get("/api/logs")
def api_logs():
    return get_logs()


@app.get("/api/history")
def api_history():
    return get_history()


@app.post("/api/pipeline/run")
async def api_pipeline_run(request: PipelineRunRequest):
    if app.state.running_task and not app.state.running_task.done():
        return {"status": "error", "message": "파이프라인이 이미 실행 중입니다"}
    task = asyncio.create_task(
        run_pipeline(
            request.input_text,
            skip_build=request.skip_build,
            skip_git=request.skip_git,
            skip_gradle=request.skip_gradle,
            skip_curl=request.skip_curl,
        )
    )
    app.state.running_task = task
    return {"status": "started", "message": "파이프라인 시작됨"}


@app.post("/api/pipeline/cancel")
async def api_pipeline_cancel():
    task = app.state.running_task
    if task and not task.done():
        task.cancel()
        return {"status": "cancelled", "message": "파이프라인 취소 요청됨"}
    return {"status": "error", "message": "실행 중인 파이프라인이 없습니다"}


@app.get("/api/pipeline/status")
async def api_pipeline_status():
    task = app.state.running_task
    is_running = task is not None and not task.done()
    return {"is_running": is_running}


@app.websocket("/ws/progress")
async def ws_progress(websocket: WebSocket):
    await websocket.accept()
    last_json = ""
    try:
        while True:
            progress = get_progress()
            current_json = progress.model_dump_json()
            if current_json != last_json:
                last_json = current_json
                await websocket.send_text(current_json)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
