"""Run a declared, already-installed local vision service; never download models.

Foreground lifecycle: keep this process alive while evaluating, then Ctrl+C to stop
its child. --check-only verifies startup/model identity and stops its own child.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
from urllib import request
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 1024 * 1024
OS_ENV = {"PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TMP", "TEMP", "HOME", "USERPROFILE",
          "LOCALAPPDATA", "APPDATA", "HOMEDRIVE", "HOMEPATH", "LANG", "LC_ALL", "LD_LIBRARY_PATH"}


def settings(profile):
    """Launcher supports the same-machine IPv4 HTTP service explicitly."""
    if (not isinstance(profile, dict) or profile.get("ACCESSFLOW_SAMSUNG_PERCEPTION") != "process"
            or profile.get("ACCESSFLOW_SAMSUNG_VISION_PROVIDER") != "ollama"):
        raise ValueError("Profile must explicitly enable process perception and Ollama vision")
    model = profile.get("ACCESSFLOW_SAMSUNG_VISION_MODEL")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,200}", model):
        raise ValueError("Invalid declared vision model")
    url = profile.get("ACCESSFLOW_SAMSUNG_VISION_URL")
    if not isinstance(url, str):
        raise ValueError("Profile needs an explicit vision URL")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid vision port") from exc
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"} or port is None or not 1024 <= port <= 65535):
        raise ValueError("Launcher requires http://127.0.0.1:<unprivileged-port> or localhost")
    return model, port


def read_json(url, timeout):
    # A local service check must not traverse proxy configuration or redirects.
    class NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=timeout) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("Vision service response exceeds the startup bound")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Vision service returned invalid startup metadata")
    return payload


def stop_child(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


@contextmanager
def service(profile, *, executable, models_dir, log_path, expected_version, expected_digest,
            timeout_s=30):
    model, port = settings(profile)
    if (not isinstance(expected_version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", expected_version)
            or not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest)):
        raise ValueError("Declare exact service version and 64-character model digest")
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not 0 < timeout_s <= 120:
        raise ValueError("Startup timeout must be within (0,120] seconds")
    executable, models_dir, log_path = Path(executable).resolve(), Path(models_dir).resolve(), Path(log_path)
    if not executable.is_file() or not models_dir.is_dir():
        raise ValueError("Install the executable and model store before starting the service")
    # Refuse occupied ports; do not reuse, reconfigure or stop another service.
    with socket.socket() as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind(("127.0.0.1", port))
    env = {key: value for key, value in os.environ.items() if key in OS_ENV}
    env.update({"OLLAMA_HOST": f"127.0.0.1:{port}", "OLLAMA_MODELS": str(models_dir),
        "OLLAMA_NO_CLOUD": "1", "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_CONTEXT_LENGTH": "4096", "OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0"})
    child = None
    started = time.monotonic()
    with log_path.open("xb") as log:
        try:
            child = subprocess.Popen([str(executable), "serve"], cwd=models_dir.parent, env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            origin = f"http://127.0.0.1:{port}"
            deadline = started + timeout_s
            while True:
                if child.poll() is not None:
                    raise RuntimeError("Vision service exited during startup; inspect its log")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Vision service startup deadline exceeded")
                try:
                    version = read_json(origin + "/api/version", min(1, remaining))
                except OSError:
                    time.sleep(min(0.1, max(0, deadline - time.monotonic())))
                    continue
                if version.get("version") != expected_version:
                    raise ValueError("Vision service version does not match the declared installation")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Vision service startup deadline exceeded")
                tags = read_json(origin + "/api/tags", min(1, remaining)).get("models")
                if not isinstance(tags, list):
                    raise ValueError("Vision model inventory is invalid")
                matching = [item for item in tags if isinstance(item, dict) and item.get("name") == model]
                if len(matching) != 1 or matching[0].get("digest") != expected_digest:
                    raise ValueError("Declared vision model is absent or its digest changed; no download attempted")
                if child.poll() is not None:
                    raise RuntimeError("Vision service exited before readiness")
                yield child, {"state": "ready", "pid": child.pid, "version": expected_version,
                    "model": model, "model_digest": expected_digest, "origin": origin,
                    "startup_s": time.monotonic() - started,
                    "inference_verified": False, "weights_downloaded": False}
                return
        finally:
            if child is not None:
                stop_child(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True, help="New log path; never overwrite an earlier run")
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-model-digest", required=True)
    parser.add_argument("--startup-timeout", type=float, default=30)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        with args.profile.open("rb") as source:
            data = source.read(65537)
        if len(data) > 65536:
            raise ValueError("Runtime profile is too large")
        profile = json.loads(data)
        with service(profile, executable=args.executable, models_dir=args.models_dir, log_path=args.log,
                     expected_version=args.expected_version, expected_digest=args.expected_model_digest,
                     timeout_s=args.startup_timeout) as (child, record):
            print(json.dumps(record), flush=True)
            if not args.check_only:
                code = child.wait()
                if code:
                    raise RuntimeError("Vision service exited unsuccessfully; inspect its log")
        print(json.dumps({"state": "stopped", "owned_child_only": True}), flush=True)
    except KeyboardInterrupt:
        print(json.dumps({"state": "stopped", "reason": "keyboard_interrupt"}), flush=True)
    except (OSError, ValueError, RuntimeError) as error:
        # File/runtime paths may be user-selected; never echo arbitrary service output.
        parser.exit(1, f"Vision startup failed ({type(error).__name__}). Check inputs and the selected log.\n")


if __name__ == "__main__":
    main()
