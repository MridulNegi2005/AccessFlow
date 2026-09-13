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
from accessflow.evaluation.replay import replay, metrics
from accessflow.turn_policy import HeuristicTurnPolicy


async def run(args):
    endpoint = urlparse(args.url)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Use the dedicated loopback Ollama server for these checks")
    os.environ["ACCESSFLOW_OLLAMA_URL"] = args.url.rstrip("/")
    os.environ["ACCESSFLOW_OLLAMA_MODEL"] = args.model
    paths = sorted(Path(args.scenarios).glob("*.json"))
    if not paths:
        raise ValueError("No scenario files found")
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=True)
    cases = []
    async with httpx.AsyncClient(timeout=30) as client:
        async def unload():
            response = await client.post(args.url + "/api/generate", json={
                "model": args.model, "keep_alive": 0, "stream": False})
            response.raise_for_status()
            loaded = await client.get(args.url + "/api/ps")
            loaded.raise_for_status()
            if any(model.get("name") == args.model for model in loaded.json().get("models", [])):
                raise RuntimeError("Model remained loaded after the unload request")

        server = await client.get(args.url + "/api/version")
        server.raise_for_status()
        tags = await client.get(args.url + "/api/tags")
        tags.raise_for_status()
        installed = [model for model in tags.json().get("models", []) if model.get("name") == args.model]
        if not installed:
            raise ValueError("Install the selected model before starting these checks")
        for index, path in enumerate(paths):
            record = {"scenario": path.name, "status": "error", "model_cleanup": "not_attempted"}
            warmup = JsonBackend("ollama")
            try:
                # This server belongs to this experiment. Unload clears model/KV
                # state between cases; only the constant warm-up precedes a case.
                await unload()
                started = time.perf_counter()
                await warmup.warmup()
                record["warmup_s"] = time.perf_counter() - started
                reasoner = ModelReasoner(JsonBackend("ollama"))
                trace = destination / f"case-{index + 1:03d}.jsonl"
                result = await replay(path, trace, reasoner=reasoner, backend=reasoner.backend.name,
                    perception=ProcessPerception(), turn_policy=HeuristicTurnPolicy(),
                    component_config={"profile": "local", "native_worker": "subprocess",
                                      "model_reset": "unload_between_cases"})
                record["result"] = result
                record["metrics"] = metrics(trace)
                record["status"] = "passed" if (
                    result["completion_status"] == "completed" and result["task_oracle"]["passed"] is True
                ) else "failed"
            except Exception as exc:
                record["exception_type"] = type(exc).__name__
            finally:
                record["warmup_evidence"] = warmup.evidence()
                try:
                    await unload()
                    record["model_cleanup"] = "unloaded"
                except Exception as exc:
                    record.update(status="error", model_cleanup="failed", cleanup_exception=type(exc).__name__)
            cases.append(record)
            report = {"backend": f"ollama/{args.model}", "server": server.json(), "installed_model": installed,
                      "case_count": len(paths), "finished_count": len(cases),
                      "counts": {status: sum(case["status"] == status for case in cases)
                                 for status in ("passed", "failed", "error")},
                      "limitation": "Live local reasoning, text inputs, mock tools, developer-authored cases; not held out.",
                      "cases": cases}
            (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"scenario": path.name, "status": record["status"],
                              "warmup_s": record.get("warmup_s"), "model_cleanup": record["model_cleanup"]}),
                  flush=True)
    return all(case["status"] == "passed" for case in cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="gemma3:4b")
    parser.add_argument("--scenarios", default="scenarios/dev")
    parser.add_argument("--output", default="artifacts/live-local")
    raise SystemExit(0 if asyncio.run(run(parser.parse_args())) else 1)
