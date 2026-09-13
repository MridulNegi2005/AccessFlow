import argparse
import asyncio
import json

from .adapters.models import JsonBackend, ModelReasoner
from .evaluation.replay import metrics, replay


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
    args = parser.parse_args()
    if args.command == "metrics":
        result = metrics(args.trace)
    elif args.command == "warmup":
        result = asyncio.run(JsonBackend(args.backend).warmup())
    else:
        backend = None if args.backend == "offline-fake" else JsonBackend(args.backend)
        result = asyncio.run(replay(args.scenario, args.output,
                            reasoner=ModelReasoner(backend) if backend else None,
                            backend=backend.name if backend else "offline-fake"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
