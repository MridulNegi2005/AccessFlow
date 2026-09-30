"""Install the frozen agent, load private configuration and run FDB supervision.

The scoring host still needs the released data, ffmpeg and a compatible Python
3.10 scorer. Supply its host-tested hashed lock to install scorer dependencies,
or explicitly reuse the prepared environment. No credentials are copied.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def bootstrap(args) -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise ValueError("Install uv before invoking the bootstrap")
    fdb, output = args.fdb_root.resolve(), args.output.resolve()
    scorer, private = args.scorer_python.resolve(), args.env_file.resolve()
    environment = args.agent_env.resolve()
    agent_python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if environment == ROOT or not environment.is_relative_to(ROOT):
        raise ValueError("Agent environment must be a subdirectory of this repository")
    if environment.exists() and (not environment.is_dir() or
            (any(environment.iterdir()) and not (environment / "pyvenv.cfg").is_file())):
        raise ValueError("Refusing to install into a nonempty directory that is not a Python environment")
    if any(path.is_relative_to(environment) for path in (fdb, output, scorer, private)):
        raise ValueError("Inputs, scorer, credentials and evidence must remain outside the managed agent environment")
    if output.exists():
        raise ValueError("Use a new output directory; existing evidence is never overwritten")
    if not fdb.is_dir() or not scorer.is_file() or not private.is_file():
        raise ValueError("Reference folder, scorer Python and private env file must exist")
    if not (ROOT / "uv.lock").is_file():
        raise ValueError("Frozen agent lock is missing")
    if scorer == agent_python.resolve():
        raise ValueError("Agent and scorer must use separate Python environments")
    if not args.reuse_scorer and (args.scorer_lock is None or not args.scorer_lock.is_file()):
        raise ValueError("Supply a host-tested hashed --scorer-lock or explicitly --reuse-scorer")
    # Never let private configuration override uv install targets/options.
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(environment)
    subprocess.run([uv, "sync", "--project", str(ROOT), "--python", "3.11",
                    "--frozen", "--no-dev", "--extra", "fdb"], check=True, cwd=ROOT, env=env)
    if not args.reuse_scorer:
        subprocess.run([uv, "pip", "install", "--python", str(scorer), "--require-hashes",
                        "--requirements", str(args.scorer_lock.resolve())], check=True, cwd=ROOT, env=env)
    command = [str(agent_python), str(ROOT / "scripts/reproduce_fdb.py"),
               "--fdb-root", str(fdb), "--scorer-python", str(scorer),
               "--env-file", str(private), "--output", str(output), "--mode", args.mode]
    if args.exact_match:
        command.append("--exact-match")
    if args.overwrite_results:
        command.append("--overwrite-results")
    subprocess.run(command, check=True, cwd=ROOT, env=env)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fdb-root", type=Path, required=True)
    parser.add_argument("--scorer-python", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True, help="Private settings file, never copied")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent-env", type=Path, default=ROOT / ".venv-fdb", help="Agent install environment")
    scorer = parser.add_mutually_exclusive_group(required=True)
    scorer.add_argument("--scorer-lock", type=Path, help="Host-tested requirements with pinned versions and hashes")
    scorer.add_argument("--reuse-scorer", action="store_true", help="Explicitly reuse a prepared scorer; does not install it")
    parser.add_argument("--mode", choices=("doctor", "run", "score", "reproduce"), default="doctor")
    parser.add_argument("--exact-match", action="store_true")
    parser.add_argument("--overwrite-results", action="store_true")
    args = parser.parse_args(argv)
    try:
        bootstrap(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(str(error) if isinstance(error, ValueError) else
              f"Bootstrap failed ({type(error).__name__}); inspect reproduction evidence if started", file=sys.stderr)
        return 1
    print(json.dumps({"status": "bootstrap_and_requested_mode_finished", "mode": args.mode}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
