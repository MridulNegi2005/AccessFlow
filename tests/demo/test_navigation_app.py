"""The local navigation display exposes only the selected room's state."""

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from accessflow.perception.navigation import NavigationStateStore

spec = importlib.util.spec_from_file_location(
    "accessflow_navigation_app", Path(__file__).parents[2] / "demo" / "navigation_app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app


def test_navigation_dashboard_and_room_state(monkeypatch, tmp_path):
    db = tmp_path / "navigation.sqlite3"
    monkeypatch.setenv("NAV_STATE_DB", str(db))
    store = NavigationStateStore(db)
    store.write("trip-1", "City Hospital", 1)
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert "Current destination" in client.get("/").text
    result = client.get("/api/navigation/trip-1")
    assert result.status_code == 200
    assert result.json()["destination"] == "City Hospital"
    assert result.json()["revision"] == 1
    assert client.get("/api/navigation/trip-2").status_code == 404
