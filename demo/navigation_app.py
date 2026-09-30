"""Local display for the separate in-car destination voice demo."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from accessflow.perception.navigation import NavigationStateStore

app = FastAPI(title="AccessFlow navigation demo")


def _store() -> NavigationStateStore:
    path = Path(os.environ.get("NAV_STATE_DB", str(
        Path(tempfile.gettempdir()) / "accessflow-navigation.sqlite3")))
    return NavigationStateStore(path)


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(Path(__file__).with_name("navigation.html"))


@app.get("/api/navigation/{room_name}")
def navigation_state(room_name: str):
    if not room_name or len(room_name) > 128:
        return JSONResponse({"error": "invalid_room"}, status_code=400)
    state = _store().read(room_name)
    if state is None:
        return JSONResponse({"error": "room_not_found"}, status_code=404)
    return state
