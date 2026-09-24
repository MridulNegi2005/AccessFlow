"""Assemble a local development package; never publish, submit, or create a tag."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from accessflow.adapters.prompt_profile import PROMPT_PROFILES
from accessflow.read_answer import READ_ANSWER_MODES

KIT_ROOT_FILES = ("eval_submission.py", "run_local.py", "README.md", "WALKTHROUGH.md")
KIT_AREAS = {"harness": {".py"}, "docs": {".md"}, "scenarios": {".json"},
             "audio": {".mp3", ".wav"}, "frames": {".png"}}
PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9][A-Za-z0-9_.+!-]*")


def pinned_requirements(export):
    """Fail on unsupported resolver output rather than producing invalid kit YAML."""
    lines = [line.strip() for line in export.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if not lines or any(not PIN.fullmatch(line) for line in lines):
        raise ValueError("This package requires flat, public-PyPI exact pins; review the lock export")
    if len({line.split("==")[0].lower().replace("_", "-") for line in lines}) != len(lines):
        raise ValueError("Duplicate dependency names in lock export")
    return sorted(lines, key=str.lower)


def profile_for(model, *, prompt_profile="full", read_answer_mode="prose"):
    if not isinstance(model, str) or not model.strip() or any(ord(c) < 32 for c in model):
        raise ValueError("Supply a nonempty model identifier without control characters")
    if prompt_profile not in PROMPT_PROFILES or read_answer_mode not in READ_ANSWER_MODES:
        raise ValueError("Unsupported prompt profile or read answer mode")
    return {
        "ACCESSFLOW_SAMSUNG_BACKEND": "groq", "ACCESSFLOW_GROQ_MODEL": model,
        "ACCESSFLOW_GROQ_URL": "https://api.groq.com/openai/v1",
        "ACCESSFLOW_GROQ_STRUCTURED": "0", "ACCESSFLOW_MAX_OUTPUT_TOKENS": "950",
        "ACCESSFLOW_MAX_CONTEXT_CHARS": "32768",
        "ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S": "1.0",
        "ACCESSFLOW_SAMSUNG_FAST_READ_RETRY": "1", "ACCESSFLOW_SAMSUNG_PROMPT_PROFILE": prompt_profile,
        "ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE": read_answer_mode,
    }


def checked_bytes(root, path):
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or path.is_symlink() or not path.is_file():
        raise ValueError(f"Package input escapes its source boundary or is not a regular file: {path.name}")
    return path.read_bytes()


def assemble(repo, kit, output, *, team, model, requirements, prompt_profile="full", read_answer_mode="prose"):
    repo, kit, output = repo.resolve(), kit.resolve(), output.resolve()
    artifact_root = (repo / "artifacts").resolve()
    if (not artifact_root.is_relative_to(repo) or not output.is_relative_to(artifact_root) or output == artifact_root
            or output.exists()):
        raise ValueError("Choose a new package directory strictly below this project's artifacts directory")
    if (not isinstance(team, str) or not team.strip() or len(team) > 100
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", team)):
        raise ValueError("Use a team label of up to100 letters, digits, spaces, dots, underscores or hyphens")
    profile = profile_for(model, prompt_profile=prompt_profile, read_answer_mode=read_answer_mode)
    requirements = pinned_requirements("\n".join(requirements))
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "src/accessflow"], cwd=repo).decode("utf-8").split("\0")
    files = {}
    for name in tracked:
        if name and Path(name).suffix == ".py":
            files[Path(name).relative_to("src").as_posix()] = checked_bytes(repo, repo / name)
    if "accessflow/adapters/samsung.py" not in files:
        raise ValueError("Tracked AccessFlow Samsung implementation is missing")
    for name in KIT_ROOT_FILES:
        files[name] = checked_bytes(kit, kit / name)
    for area, extensions in KIT_AREAS.items():
        folder = kit / area
        if not folder.is_dir():
            raise ValueError(f"Supplied kit is missing {area}")
        for path in sorted(folder.rglob("*")):
            if "__pycache__" not in path.parts and path.suffix.lower() in extensions:
                files[path.relative_to(kit).as_posix()] = checked_bytes(kit, path)
    for required in ("harness/runner.py", "harness/scorer.py", "docs/TOOLS.md"):
        if required not in files:
            raise ValueError(f"Supplied kit is missing {required}")
    files["agent/__init__.py"] = b""
    files["agent/agent.py"] = checked_bytes(repo, repo / "scripts/submission_entry.py")
    for name in ("pyproject.toml", "uv.lock"):
        files[f"build_inputs/{name}"] = checked_bytes(repo, repo / name)
    yaml = [f'team: "{team}"', 'entry_point: "agent.agent:ParticipantAgent"', 'python: "3.11"',
            "requirements:", *[f"  - {item}" for item in requirements], "env:", "  - SECRET_GROQ_API_KEY"]
    files["submission.yaml"] = ("\n".join(yaml) + "\n").encode()
    files["requirements.txt"] = ("\n".join(requirements) + "\n").encode()
    files["runtime_profile.json"] = (json.dumps(profile, indent=2) + "\n").encode()
    files["PACKAGE_NOTES.md"] = (
        "# Local development package\n\n"
        "Install requirements.txt in a fresh Python3.11 environment. Supply SECRET_GROQ_API_KEY.\n"
        "Run from this directory: python eval_submission.py . --reps 3\n"
        "This runs hosted inference and consumes the configured provider quota.\n"
        "The default profile is declared in runtime_profile.json; conflicting environment values fail.\n"
        "No credential, model weights, private recording, or release tag is included.\n"
        "Organizer source/public scenarios/media are copied for local reproducibility.\n"
        "Do not publish the generated directory as repository source.\n"
        "MP3 assembly/vision wiring remain incomplete. Packaging does not certify multimodal quality.\n"
        "No official repeated-run score, clean install, or Docker result is implied by assembly.\n"
    ).encode()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo))
    manifest = {"base_commit": commit, "source_dirty": dirty,
                "purpose": "local-development-package; not a submitted release",
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
    # All input validation precedes creation. Never delete or overwrite an old artifact.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output / "package_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--team", required=True, help="Local package label; confirm registered spelling before submission")
    parser.add_argument("--model", required=True, help="Explicit Groq model; no fallback")
    parser.add_argument("--prompt-profile", choices=sorted(PROMPT_PROFILES), default="full")
    parser.add_argument("--read-answer-mode", choices=sorted(READ_ANSWER_MODES), default="prose")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    export = subprocess.check_output(
        ["uv", "export", "--offline", "--frozen", "--format", "requirements-txt", "--no-dev",
         "--no-emit-project", "--no-hashes"], cwd=repo, text=True)
    try:
        manifest = assemble(repo, args.kit, args.output, team=args.team, model=args.model,
                            requirements=pinned_requirements(export), prompt_profile=args.prompt_profile,
                            read_answer_mode=args.read_answer_mode)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"package": str(args.output.resolve()), "files": len(manifest["files"]),
                      "source_dirty": manifest["source_dirty"], "submitted": False}))


if __name__ == "__main__":
    main()
