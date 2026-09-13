import argparse
import asyncio
import json
from pathlib import Path

from .adapters.models import JsonBackend, ModelReasoner
from .evaluation.replay import metrics, replay
from .evaluation.suite import run_suite


def main():
    parser = argparse.ArgumentParser(description="AccessFlow internal development harness")
    commands = parser.add_subparsers(dest="command", required=True)
    replay_parser = commands.add_parser("replay")
    replay_parser.add_argument("scenario")
    replay_parser.add_argument("--output", default="artifacts/replay.jsonl")
    replay_parser.add_argument("--backend", choices=["offline-fake", "ollama", "gemini"], default="offline-fake")
    metrics_parser = commands.add_parser("metrics")
    metrics_parser.add_argument("trace")
    warmup = commands.add_parser("warmup")
    warmup.add_argument("--backend", choices=["ollama", "gemini"], required=True)
    suite = commands.add_parser("suite")
    suite.add_argument("scenario_directory")
    suite.add_argument("--output-dir", default="artifacts/suite")
    suite.add_argument("--backend", choices=["offline-fake", "ollama", "gemini"], default="offline-fake")
    args = parser.parse_args()
    if args.command == "metrics":
        result = metrics(args.trace)
    elif args.command == "warmup":
        result = asyncio.run(JsonBackend(args.backend).warmup())
    elif args.command == "suite":
        backend = None if args.backend == "offline-fake" else JsonBackend(args.backend)
        report = asyncio.run(run_suite(Path(args.scenario_directory).glob("*.json"), args.output_dir,
                    reasoner_factory=(lambda: ModelReasoner(JsonBackend(args.backend))) if backend else None,
                    backend=backend.name if backend else "offline-fake"))
        result = {key: value for key, value in report.items() if key != "cases"}
        result["report"] = str(Path(args.output_dir) / "report.json")
        print(json.dumps(result, indent=2))
        if report["counts"]["failed"] or report["counts"]["error"]:
            raise SystemExit(1)
        return
    else:
        backend = None if args.backend == "offline-fake" else JsonBackend(args.backend)
        result = asyncio.run(replay(args.scenario, args.output,
                            reasoner=ModelReasoner(backend) if backend else None,
                            backend=backend.name if backend else "offline-fake"))
    print(json.dumps(result, indent=2))
    if args.command == "replay" and (
            result["completion_status"] != "completed" or result["task_oracle"]["passed"] is False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
