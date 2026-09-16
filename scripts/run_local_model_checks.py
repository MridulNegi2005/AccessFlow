"""Explicit local-model development checks; mock effects and no official score."""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.adapters.process_perception import ProcessPerception
from accessflow.contracts import PlanProposal
from accessflow.evaluation.replay import replay, metrics
from accessflow.turn_policy import HeuristicTurnPolicy


class ModelIsolationError(RuntimeError):
    """A model reset could not establish an empty server state."""

    def __init__(self, reason, observation):
        super().__init__(reason)
        self.reason = reason
        self.observation = observation


class DiagnosticReasoner:
    """Keep per-run typed plans alongside the content-free replay telemetry."""

    def __init__(self, delegate):
        self.delegate = delegate
        self.plans = []

    async def plan(self, view, manifests):
        proposal = await self.delegate.plan(view, manifests)
        proposal = PlanProposal.model_validate(proposal)
        self.plans.append({
            "state_revision": view.state.revision,
            "observation_event_ids": [observation.event_id for observation in view.observations],
            "proposal": proposal.model_dump(mode="json"),
        })
        return proposal

    def evidence(self):
        return self.delegate.evidence()


def _failure(exc, phase):
    result = {"phase": phase, "exception_type": type(exc).__name__}
    if isinstance(exc, ModelIsolationError):
        result["reason_code"] = exc.reason
        result["model_observation"] = exc.observation
    return result


def _report(*, args, paths, cases, server, installed, status, setup_failure=None, run_failure=None):
    counts = {name: sum(case["status"] == name for case in cases)
              for name in ("passed", "failed", "error", "cancelled")}
    counts["not_run"] = len(paths) - len(cases)
    result = {
        "backend": f"ollama/{args.model}", "server": server, "installed_model": installed,
        "case_count": len(paths), "finished_count": len(cases),
        "not_run_count": len(paths) - len(cases), "counts": counts, "status": status,
        "limitation": "Live local reasoning, text inputs, mock tools, developer-authored cases; not held out.",
        "cases": cases,
    }
    if setup_failure is not None:
        result["setup_failure"] = setup_failure
    if run_failure is not None:
        result["run_failure"] = run_failure
    return result


async def run(args, *, client_factory=None, backend_factory=None, replay_fn=None):
    endpoint = urlparse(args.url)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Use the dedicated loopback Ollama server for these checks")
    base_url = args.url.rstrip("/")
    os.environ["ACCESSFLOW_OLLAMA_URL"] = base_url
    os.environ["ACCESSFLOW_OLLAMA_MODEL"] = args.model
    paths = sorted(Path(args.scenarios).glob("*.json"))
    if not paths:
        raise ValueError("No scenario files found")
    destination = Path(args.output)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Output directory must be an empty directory")
    destination.mkdir(parents=True, exist_ok=True)
    cases = []
    server = None
    installed = None
    def write_report(**kwargs):
        report = _report(args=args, paths=paths, cases=cases, server=server, installed=installed, **kwargs)
        destination.joinpath("report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_report(status="setup_pending")
    if client_factory is None:
        def client_factory():
            return httpx.AsyncClient(timeout=30)
    if backend_factory is None:
        def backend_factory():
            return JsonBackend("ollama")
    if replay_fn is None:
        replay_fn = replay
    async with client_factory() as client:
        async def loaded_models():
            response = await client.get(base_url + "/api/ps")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
                raise RuntimeError("Invalid model process list")
            names = []
            for model in payload["models"]:
                if not isinstance(model, dict) or not isinstance(model.get("name"), str):
                    raise RuntimeError("Invalid model process entry")
                names.append(model["name"])
            return names

        last_reset = {"before": None, "after": None}

        async def reset_model():
            nonlocal last_reset
            last_reset = {"before": None, "after": None}
            last_reset["before"] = await loaded_models()
            unexpected = sorted({name for name in last_reset["before"] if name != args.model})
            if unexpected:
                raise ModelIsolationError("unexpected_loaded_model", last_reset)
            if args.model in last_reset["before"]:
                response = await client.post(base_url + "/api/generate", json={
                    "model": args.model, "keep_alive": 0, "stream": False})
                response.raise_for_status()
            last_reset["after"] = await loaded_models()
            if last_reset["after"]:
                raise ModelIsolationError("models_remained_loaded", last_reset)

        try:
            response = await client.get(base_url + "/api/version")
            response.raise_for_status()
            server = response.json()
            tags = await client.get(base_url + "/api/tags")
            tags.raise_for_status()
            payload = tags.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
                raise RuntimeError("Invalid installed model list")
            installed = [model for model in payload["models"]
                         if isinstance(model, dict) and model.get("name") == args.model]
            if not installed:
                raise ValueError("Install the selected model before starting these checks")
        except asyncio.CancelledError as exc:
            write_report(status="cancelled", setup_failure=_failure(exc, "setup"))
            raise
        except Exception as exc:
            write_report(status="error", setup_failure=_failure(exc, "setup"))
            return False

        for index, path in enumerate(paths):
            record = {"scenario": path.name, "status": "error", "model_cleanup": "not_attempted"}
            warmup = None
            diagnostic_reasoner = None
            cleanup_failed = False
            cancelled = False
            phase = "initialize"
            try:
                warmup = backend_factory()
                phase = "pre_reset"
                await reset_model()
                record["model_reset"] = last_reset
                phase = "warmup"
                started = time.perf_counter()
                await warmup.warmup()
                record["warmup_s"] = time.perf_counter() - started
                placement = await client.get(base_url + "/api/ps")
                placement.raise_for_status()
                record["model_placement_after_warmup"] = placement.json()
                phase = "replay"
                diagnostic_reasoner = DiagnosticReasoner(ModelReasoner(backend_factory()))
                trace = destination / f"case-{index + 1:03d}.jsonl"
                result = await replay_fn(path, trace, reasoner=diagnostic_reasoner,
                    backend=diagnostic_reasoner.delegate.backend.name,
                    perception=ProcessPerception(), turn_policy=HeuristicTurnPolicy(),
                    component_config={"profile": "local", "native_worker": "subprocess",
                                      "model_reset": "unload_between_cases"})
                record["result"] = result
                record["metrics"] = metrics(trace)
                record["status"] = "passed" if (
                    result["completion_status"] == "completed" and result["task_oracle"]["passed"] is True
                ) else "failed"
            except asyncio.CancelledError as exc:
                cancelled = True
                record.update(status="cancelled", failure=_failure(exc, phase))
            except Exception as exc:
                record["failure"] = _failure(exc, phase)
            finally:
                if diagnostic_reasoner is not None:
                    record["plans"] = diagnostic_reasoner.plans
                record["warmup_evidence"] = warmup.evidence() if warmup is not None else None
                try:
                    await reset_model()
                    record["model_cleanup_observation"] = last_reset
                    record["model_cleanup"] = "unloaded"
                except Exception as exc:
                    cleanup_failed = True
                    record.update(status="error", model_cleanup="failed",
                                  cleanup_failure=_failure(exc, "cleanup"),
                                  model_cleanup_observation=last_reset)
            cases.append(record)
            write_report(status="cancelled" if cancelled else "error" if cleanup_failed else "running")
            print(json.dumps({"scenario": path.name, "status": record["status"],
                              "warmup_s": record.get("warmup_s"), "model_cleanup": record["model_cleanup"]}),
                  flush=True)
            if cancelled:
                raise asyncio.CancelledError()
            if cleanup_failed:
                break
        final_status = "passed" if len(cases) == len(paths) and all(
            case["status"] == "passed" for case in cases) else "failed"
        write_report(status=final_status)
    return final_status == "passed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="gemma3:4b")
    parser.add_argument("--scenarios", default="scenarios/live_dev")
    parser.add_argument("--output", default="artifacts/live-local")
    raise SystemExit(0 if asyncio.run(run(parser.parse_args())) else 1)
