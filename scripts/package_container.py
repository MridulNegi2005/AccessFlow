"""Container build files for a generated Samsung evaluator package."""


# Keep this list aligned with the generated package, not the repository root.
COPY_PATHS = (
    "accessflow/",
    "agent/",
    "harness/",
    "docs/",
    "scenarios/",
    "audio/",
    "frames/",
    "assets/",
    "hosting/start_vision_server.py",
    "submission.yaml",
    "runtime_profile.json",
    "eval_submission.py",
    "run_local.py",
    "package_manifest.json",
)


def container_files() -> dict[str, bytes]:
    """Return Docker build files for the generated-package root."""
    dockerfile = """FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \\
    && apt-get install -y --no-install-recommends libgomp1 \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt

RUN groupadd --gid 10001 accessflow \\
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin accessflow \\
    && mkdir -p /results \\
    && chown accessflow:accessflow /results

"""
    def copy_instruction(path):
        if path.endswith("/"):
            destination = f"./{path.rstrip('/')}"
        elif path.startswith("hosting/"):
            destination = "./hosting/"
        else:
            destination = "./"
        return f"COPY {path} {destination}\n"

    dockerfile += "".join(copy_instruction(path) for path in COPY_PATHS)
    dockerfile += """

USER 10001:10001
ENTRYPOINT ["python", "eval_submission.py"]
CMD [".", "--reps", "3", "--out", "/results/results.json"]
"""

    # Deny the whole build context, then admit only generated package inputs.
    # Keep the final deny rules after the allowlist: Docker applies the last
    # matching rule, so credential-like files and generated debris stay out.
    dockerignore = """**
"""
    dockerignore += "!requirements.txt\n"
    dockerignore += "".join(f"!{path}\n" for path in COPY_PATHS)
    dockerignore += """!accessflow/**
!agent/**
!harness/**
!docs/**
!scenarios/**
!audio/**
!frames/**
!assets/**
!hosting/
**/.env*
**/credentials
**/credentials.*
**/*_credentials.*
**/*-credentials.*
**/secret
**/secret.*
**/secrets.*
**/*_secret.*
**/*-secret.*
**/*api_key*
**/*api-key*
**/*apikey*
**/*.pem
**/*.key
**/*id_rsa*
**/__pycache__
**/__pycache__/**
**/.pytest_cache
**/.pytest_cache/**
**/.mypy_cache
**/.mypy_cache/**
**/.ruff_cache
**/.ruff_cache/**
**/.venv
**/.venv/**
**/venv
**/venv/**
**/node_modules
**/node_modules/**
**/output
**/output/**
**/outputs
**/outputs/**
**/results
**/results/**
**/*.log
"""
    return {
        "Dockerfile": dockerfile.encode("utf-8"),
        ".dockerignore": dockerignore.encode("utf-8"),
    }
