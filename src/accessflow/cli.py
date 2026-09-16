import argparse
import asyncio
import json
import math
import os
from pathlib import Path

from .adapters.models import JsonBackend, ModelReasoner
from .engine import Agent
from .evaluation.replay import metrics, replay
from .evaluation.suite import run_suite
from .evaluation.responsiveness import run_responsiveness


def main():
    parser = argparse.ArgumentParser(description="AccessFlow internal development harness")
    commands = parser.add_subparsers(dest="command", required=True)
    replay_parser = commands.add_parser("replay")
    replay_parser.add_argument("scenario")
    replay_parser.add_argument("--output", default="artifacts/replay.jsonl")
    replay_parser.add_argument("--backend", choices=["offline-fake", "ollama", "gemini", "groq", "nvidia"], default="offline-fake")
    metrics_parser = commands.add_parser("metrics")
    metrics_parser.add_argument("trace")
    warmup = commands.add_parser("warmup")
    warmup.add_argument("--backend", choices=["ollama", "gemini", "groq", "nvidia"], required=True)
    suite = commands.add_parser("suite")
    suite.add_argument("scenario_directory")
    suite.add_argument("--output-dir", default="artifacts/suite")
    suite.add_argument("--backend", choices=["offline-fake", "ollama", "gemini", "groq", "nvidia"], default="offline-fake")
    for component_parser in (replay_parser, suite):
        component_parser.add_argument("--components", choices=["fake", "local"], default="fake",
                                      help="Use fakes or process-isolated local media plus HeuristicTurnPolicy")
        component_parser.add_argument("--asr-model-path", type=Path,
                                      help="Already-installed Faster Whisper directory; requires --components local")
        component_parser.add_argument("--vision-provider", choices=["none", "ollama"], default="none",
                                      help="Vision backend for frame events; requires --components local")
        component_parser.add_argument("--vision-model", default=None,
                                      help="Vision model name; defaults to the provider's own default")
        component_parser.add_argument("--vision-url", default=None,
                                      help="Vision backend URL; defaults to the provider's own default")
    for model_parser in (replay_parser, suite, warmup):
        model_parser.add_argument("--request-timeout", type=float, default=20.0,
                                  help="Seconds allowed per model request; record it with any result")
    for deadline_parser in (replay_parser, suite):
        deadline_parser.add_argument("--disable", action="append", default=[],
                                     choices=sorted(Agent.ABLATIONS),
                                     help="Switch off one engine component for a baseline comparison. "
                                          "Everything else stays identical.")
        deadline_parser.add_argument("--inference-timeout", type=float,
                                     help="Controller deadline per planning step; defaults to the Agent value")
        deadline_parser.add_argument("--corpus-root", type=Path, default=None,
                                     help="Trusted directory of installable corpus documents, for scenarios "
                                          "that declare Start.corpus; sets ACCESSFLOW_CORPUS_ROOT for the run")
    responsiveness = commands.add_parser("responsiveness", help="Measure synthetic controller responsiveness")
    responsiveness.add_argument("--samples", type=int, default=100, help="Independent samples per condition")
    responsiveness.add_argument("--output-dir", default="artifacts/responsiveness")
    args = parser.parse_args()
    request_timeout = getattr(args, "request_timeout", 1.0)
    if request_timeout <= 0 or not math.isfinite(request_timeout):
        parser.error("--request-timeout must be positive")
    if getattr(args, "inference_timeout", None) is not None and (
        args.inference_timeout <= 0 or not math.isfinite(args.inference_timeout)
    ):
        parser.error("--inference-timeout must be positive")
    perception_factory = policy_factory = None
    component_config = {}
    if args.command in {"suite", "replay"}:
        if args.asr_model_path is not None and args.components != "local":
            parser.error("--asr-model-path requires --components local")
        if args.vision_provider != "none" and args.components != "local":
            parser.error("--vision-provider requires --components local")
        if args.corpus_root is not None and not args.corpus_root.is_dir():
            parser.error("--corpus-root must be an existing directory")
        # Threaded to Agent through ACCESSFLOW_CORPUS_ROOT (see engine.Agent.__init__)
        # rather than a new constructor path here: this is the only normal-harness route
        # into replay()/run_suite(), which construct Agent themselves and are not part of
        # this fix's owned files. Recorded in component_config (already plumbed verbatim
        # into replay's trace metadata) so the resolved root is visible in evidence
        # without ever being sent to the planner itself -- see corpus.corpus_manifest,
        # which only ever exposes logical document names, never a filesystem path.
        resolved_corpus_root = str(args.corpus_root.resolve()) if args.corpus_root is not None else None
        if resolved_corpus_root is not None:
            os.environ["ACCESSFLOW_CORPUS_ROOT"] = resolved_corpus_root
        component_config = {"profile": args.components,
                            "corpus_root": resolved_corpus_root or os.environ.get("ACCESSFLOW_CORPUS_ROOT")}
        if args.components == "local":
            from .adapters.process_perception import ProcessPerception
            from .turn_policy import HeuristicTurnPolicy
            worker_args = []
            if args.vision_provider != "none":
                worker_args += ["--vision-provider", args.vision_provider]
                if args.vision_model:
                    worker_args += ["--vision-model", args.vision_model]
                if args.vision_url:
                    worker_args += ["--vision-url", args.vision_url]
            def perception_factory():
                return ProcessPerception(model_path=args.asr_model_path, worker_args=worker_args)
            policy_factory = HeuristicTurnPolicy
            component_config["asr_model_path"] = str(args.asr_model_path) if args.asr_model_path else None
            if args.vision_provider == "none":
                component_config["vision_provider_requested"] = "none"
            else:
                from .adapters.vision import DEFAULT_MODEL as vision_default_model
                resolved_vision_model = args.vision_model or os.getenv(
                    "ACCESSFLOW_VISION_OLLAMA_MODEL", vision_default_model)
                # What the parent asked for, never proof that the child honoured it. The
                # child rejects these options today, so a resolved-sounding name here would
                # claim a vision backend that never ran. The observation backend field is
                # the evidence of what actually served a frame. See CONTRACT_PROPOSALS.md.
                component_config["vision_provider_requested"] = (
                    f"{args.vision_provider}/{resolved_vision_model}")
            component_config["native_worker"] = "subprocess"
    if args.command == "metrics":
        result = metrics(args.trace)
    elif args.command == "warmup":
        result = asyncio.run(JsonBackend(args.backend, timeout=args.request_timeout).warmup())
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
        backend = None if args.backend == "offline-fake" else JsonBackend(args.backend, timeout=args.request_timeout)
        report = asyncio.run(run_suite(Path(args.scenario_directory).glob("*.json"), args.output_dir,
                    reasoner_factory=(lambda: ModelReasoner(
                        JsonBackend(args.backend, timeout=args.request_timeout))) if backend else None,
                    backend=backend.name if backend else "offline-fake",
                    perception_factory=perception_factory, turn_policy_factory=policy_factory,
                    component_config=component_config, inference_timeout=args.inference_timeout,
                    disabled=tuple(args.disable)))
        result = {key: value for key, value in report.items() if key != "cases"}
        result["report"] = str(Path(args.output_dir) / "report.json")
        print(json.dumps(result, indent=2))
        if report["counts"]["failed"] or report["counts"]["error"]:
            raise SystemExit(1)
        return
    else:
        backend = None if args.backend == "offline-fake" else JsonBackend(args.backend, timeout=args.request_timeout)
        result = asyncio.run(replay(args.scenario, args.output,
                            reasoner=ModelReasoner(backend) if backend else None,
                            backend=backend.name if backend else "offline-fake",
                            perception=perception_factory() if perception_factory else None,
                            turn_policy=policy_factory() if policy_factory else None,
                            component_config=component_config, inference_timeout=args.inference_timeout,
                    disabled=tuple(args.disable)))
    print(json.dumps(result, indent=2))
    if args.command == "replay" and (
            result["completion_status"] != "completed" or result["task_oracle"]["passed"] is False):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
