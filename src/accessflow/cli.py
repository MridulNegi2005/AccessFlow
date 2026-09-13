import argparse
import asyncio
import json
from pathlib import Path

from .adapters.models import JsonBackend, ModelReasoner
from .evaluation.replay import metrics, replay
from .evaluation.suite import run_suite
from .evaluation.responsiveness import run_responsiveness


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
    for component_parser in (replay_parser, suite):
        component_parser.add_argument("--components", choices=["fake", "local"], default="fake",
                                      help="Use fakes or LocalPerception plus HeuristicTurnPolicy")
        component_parser.add_argument("--asr-model-path", type=Path,
                                      help="Already-installed Faster Whisper directory; requires --components local")
    responsiveness = commands.add_parser("responsiveness", help="Measure synthetic controller responsiveness")
    responsiveness.add_argument("--samples", type=int, default=100, help="Independent samples per condition")
    responsiveness.add_argument("--output-dir", default="artifacts/responsiveness")
    args = parser.parse_args()
    perception_factory = policy_factory = None
    component_config = {}
    if args.command in {"suite", "replay"}:
        if args.asr_model_path is not None and args.components != "local":
            parser.error("--asr-model-path requires --components local")
        component_config = {"profile": args.components}
        if args.components == "local":
            from .perception import LocalPerception
            from .turn_policy import HeuristicTurnPolicy
            def perception_factory():
                return LocalPerception(model_path=args.asr_model_path)
            policy_factory = HeuristicTurnPolicy
            component_config["asr_model_path"] = str(args.asr_model_path) if args.asr_model_path else None
            component_config["vision_provider"] = "not_configured"
    if args.command == "metrics":
        result = metrics(args.trace)
    elif args.command == "warmup":
        result = asyncio.run(JsonBackend(args.backend).warmup())
    elif args.command == "responsiveness":
        if args.samples < 1:
            parser.error("--samples must be positive")
        result = asyncio.run(run_responsiveness(args.output_dir, samples=args.samples))
        print(json.dumps(result, indent=2))
        if result["counts"]["failed"] or any(
                target["target_passed"] is not True for target in result["targets"].values()):
            raise SystemExit(1)
        return
    elif args.command == "suite":
        backend = None if args.backend == "offline-fake" else JsonBackend(args.backend)
        report = asyncio.run(run_suite(Path(args.scenario_directory).glob("*.json"), args.output_dir,
                    reasoner_factory=(lambda: ModelReasoner(JsonBackend(args.backend))) if backend else None,
                    backend=backend.name if backend else "offline-fake",
                    perception_factory=perception_factory, turn_policy_factory=policy_factory,
                    component_config=component_config))
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
                            backend=backend.name if backend else "offline-fake",
                            perception=perception_factory() if perception_factory else None,
                            turn_policy=policy_factory() if policy_factory else None,
                            component_config=component_config))
    print(json.dumps(result, indent=2))
    if args.command == "replay" and (
            result["completion_status"] != "completed" or result["task_oracle"]["passed"] is False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
