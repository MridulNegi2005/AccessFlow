"""Container recipe safety and evaluator defaults for generated packages."""

from fnmatch import fnmatchcase

from scripts.package_container import COPY_PATHS, container_files


def test_container_recipe_copies_only_the_generated_package_allowlist():
    files = container_files()
    dockerfile = files["Dockerfile"].decode()
    copied_sources = tuple(
        line.split()[1]
        for line in dockerfile.splitlines()
        if line.startswith("COPY ")
    )
    copy_targets = {
        source: target
        for source, target in (line.split()[1:3] for line in dockerfile.splitlines() if line.startswith("COPY "))
    }

    assert copied_sources == ("requirements.txt", *COPY_PATHS)
    assert "COPY . " not in dockerfile
    assert "FROM python:3.11-slim-bookworm" in dockerfile
    assert "--only-binary=:all:" in dockerfile
    assert copy_targets["eval_submission.py"] == "./"
    assert copy_targets["run_local.py"] == "./"
    assert copy_targets["hosting/start_vision_server.py"] == "./hosting/"
    assert "libgomp1" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert 'ENTRYPOINT ["python", "eval_submission.py"]' in dockerfile
    assert 'CMD [".", "--reps", "3", "--out", "/results/results.json"]' in dockerfile
    assert "mkdir -p /results" in dockerfile


def test_dockerignore_is_default_deny_and_excludes_credentials_and_build_debris():
    dockerignore = container_files()[".dockerignore"].decode().splitlines()

    assert dockerignore[0] == "**"
    for path in COPY_PATHS:
        assert f"!{path}" in dockerignore
    assert "!hosting/" in dockerignore
    assert "!hosting/**" not in dockerignore
    assert "**/.env*" in dockerignore
    assert "**/credentials.*" in dockerignore
    assert "**/secrets.*" in dockerignore
    assert "**/*api_key*" in dockerignore
    assert not any("token" in rule.lower() for rule in dockerignore)
    assert "**/__pycache__/**" in dockerignore
    assert "**/.venv/**" in dockerignore
    assert "**/models/**" not in dockerignore


def test_real_asr_tokenizer_file_is_not_excluded_by_effective_dockerignore_rules():
    patterns = container_files()[".dockerignore"].decode().splitlines()

    def is_ignored(path):
        ignored = False
        for pattern in patterns:
            include = pattern.startswith("!")
            candidate = pattern[1:] if include else pattern
            if fnmatchcase(path, candidate):
                ignored = not include
        return ignored

    assert not is_ignored("assets/asr/tokenizer.json")
    assert is_ignored("assets/asr/credentials.json")
    assert is_ignored("assets/asr/private.key")
