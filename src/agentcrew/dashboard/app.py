"""FastAPI 앱 + 라우트 정의."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agentcrew.dashboard.services import (
    get_config,
    get_history,
    get_logs,
    get_progress,
    get_tasks,
)

app = FastAPI(title="AgentCrew Dashboard API", version="0.1.0")

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
