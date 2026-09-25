"""Hosting lifecycle uses a real child serving fake metadata, never model evidence."""

import json
import socket
import sys

import pytest

from scripts import start_vision_server as hosting


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def profile(port):
    return {"ACCESSFLOW_SAMSUNG_PERCEPTION": "process", "ACCESSFLOW_SAMSUNG_VISION_PROVIDER": "ollama",
            "ACCESSFLOW_SAMSUNG_VISION_MODEL": "fixture:tiny",
            "ACCESSFLOW_SAMSUNG_VISION_URL": f"http://127.0.0.1:{port}"}


@pytest.fixture
def fixture_service(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    # Python is the executable, and its `serve` positional argument names this file.
    (tmp_path / "serve").write_text('''
import json, os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
Path('child_environment.json').write_text(json.dumps(dict(os.environ)))
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        value = {'version':'1.2.3'} if self.path == '/api/version' else {'models':[{'name':'fixture:tiny','digest':'a'*64}]}
        body=json.dumps(value).encode()
        self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *args): pass
HTTPServer(('127.0.0.1',int(os.environ['OLLAMA_HOST'].rsplit(':',1)[1])),Handler).serve_forever()
''', encoding="utf-8")
    original = hosting.subprocess.Popen
    children = []

    def capture(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(hosting.subprocess, "Popen", capture)
    options = dict(executable=sys.executable, models_dir=models, log_path=tmp_path / "service.log",
                   expected_version="1.2.3", expected_digest="a" * 64, timeout_s=5)
    yield profile(unused_port()), options, children
    for child in children:
        hosting.stop_child(child)


def test_real_child_readiness_identity_environment_and_owned_cleanup(fixture_service, tmp_path, monkeypatch):
    config, options, children = fixture_service
    monkeypatch.setenv("SECRET_GROQ_API_KEY", "fake-must-not-inherit")
    monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0:31337")
    monkeypatch.setenv("OLLAMA_NUM_PARALLEL", "99")
    with hosting.service(config, **options) as (child, record):
        assert child is children[0] and child.poll() is None
        assert record["state"] == "ready" and record["model_digest"] == "a" * 64
        assert not record["inference_verified"] and not record["weights_downloaded"]
        env = json.loads((tmp_path / "child_environment.json").read_text())
        assert "SECRET_GROQ_API_KEY" not in env
        assert env["OLLAMA_HOST"].startswith("127.0.0.1:")
        assert env["OLLAMA_NUM_PARALLEL"] == "1" and env["OLLAMA_NO_CLOUD"] == "1"
    assert child.poll() is not None


@pytest.mark.parametrize("override", [{"expected_version": "9.9.9"}, {"expected_digest": "b" * 64}])
def test_wrong_installation_identity_stops_launched_child(fixture_service, override):
    config, options, children = fixture_service
    with pytest.raises(ValueError, match="version|digest"):
        with hosting.service(config, **(options | override)):
            pytest.fail("Wrong installed identity was accepted")
    assert len(children) == 1 and children[0].poll() is not None


def test_missing_model_stops_launched_child(fixture_service):
    config, options, children = fixture_service
    config["ACCESSFLOW_SAMSUNG_VISION_MODEL"] = "absent:model"
    with pytest.raises(ValueError, match="absent"):
        with hosting.service(config, **options):
            pytest.fail("Missing model was accepted")
    assert children[0].poll() is not None


def test_setup_deadline_cleans_up_child(fixture_service, tmp_path):
    config, options, children = fixture_service
    (tmp_path / "serve").write_text("import time; time.sleep(60)", encoding="utf-8")
    with pytest.raises(TimeoutError):
        with hosting.service(config, **(options | {"timeout_s": 0.2})):
            pytest.fail("Silent child was marked ready")
    assert children[0].poll() is not None


def test_child_exit_is_failure(fixture_service, tmp_path):
    config, options, children = fixture_service
    (tmp_path / "serve").write_text("raise SystemExit(4)", encoding="utf-8")
    with pytest.raises(RuntimeError, match="exited"):
        with hosting.service(config, **options):
            pytest.fail("Exited child was marked ready")
    assert children[0].returncode == 4


def test_occupied_port_is_not_reused_or_terminated(fixture_service):
    _, options, children = fixture_service
    with socket.socket() as existing:
        existing.bind(("127.0.0.1", 0))
        existing.listen()
        config = profile(existing.getsockname()[1])
        with pytest.raises(OSError):
            with hosting.service(config, **options):
                pytest.fail("Occupied port was reused")
        assert existing.fileno() >= 0 and not children


def test_existing_log_preserved_without_starting_child(fixture_service):
    config, options, children = fixture_service
    options["log_path"].write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        with hosting.service(config, **options):
            pytest.fail("Existing log overwritten")
    assert not children and options["log_path"].read_text() == "keep"


@pytest.mark.parametrize("url", ["http://0.0.0.0:11435", "http://example.test:11435",
    "http://name:password@localhost:11435", "http://@localhost:11435", "https://localhost:11435", "http://localhost:11435/api",
    "http://localhost:11435?x=y", "http://localhost:80", "http://localhost:not-a-port"])
def test_invalid_binding_rejected_before_spawn(fixture_service, url):
    config, options, children = fixture_service
    config["ACCESSFLOW_SAMSUNG_VISION_URL"] = url
    with pytest.raises(ValueError):
        with hosting.service(config, **options):
            pytest.fail("Invalid service binding accepted")
    assert not children
