"""Portable package boundaries, declared configuration and credential handling."""

import asyncio
import hashlib
import json

import pytest

from scripts import build_samsung_package as builder
from scripts import submission_entry as entry


@pytest.mark.parametrize("invalid", ["", "thing>=2", "thing @ https://example.test/thing.whl",
                                    "-e .", 'thing==2; python_version < "3.12"', "thing==2\nthing==3"])
def test_pins_reject_nonportable_or_ambiguous_exports(invalid):
    with pytest.raises(ValueError):
        builder.pinned_requirements(invalid)


def test_pins_discard_comments_without_losing_versions():
    assert builder.pinned_requirements("# generated\nzeta==2.1\n # via project\nalpha==1.0rc1\n") == [
        "alpha==1.0rc1", "zeta==2.1"]


def test_profile_maps_portal_secret_without_copying_it_into_profile():
    profile = builder.profile_for("declared/model")
    environment = {"SECRET_GROQ_API_KEY": "private-test-key", "UNRELATED": "retained"}
    entry.configure_profile(profile, environment)
    entry.configure_profile(profile, environment)  # Repeated scenarios reuse static configuration.
    assert environment["ACCESSFLOW_GROQ_API_KEY"] == "private-test-key"
    assert environment["UNRELATED"] == "retained"
    assert "private-test-key" not in json.dumps(profile)
    assert set(profile) == entry.PROFILE_KEYS


def test_default_package_refuses_inherited_evidence_mode_without_mutation():
    environment = {"SECRET_GROQ_API_KEY": "private-test-key",
                   "ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE": "evidence"}
    before = dict(environment)
    with pytest.raises(ValueError, match="READ_ANSWER_MODE"):
        entry.configure_profile(builder.profile_for("declared/model"), environment)
    assert environment == before


@pytest.mark.parametrize("name", sorted(entry.PERCEPTION_ENV_KEYS))
def test_text_package_refuses_inherited_native_perception_before_mutation(name):
    environment = {"SECRET_GROQ_API_KEY": "private-test-key", name: "process"}
    before = dict(environment)
    with pytest.raises(ValueError, match="perception|PERCEPTION"):
        entry.configure_profile(builder.profile_for("declared/model"), environment)
    assert environment == before


def test_native_profile_cannot_claim_assets_installed_by_text_builder():
    profile = builder.profile_for("declared/model")
    profile["ACCESSFLOW_SAMSUNG_PERCEPTION"] = "process"
    environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
    with pytest.raises(ValueError, match="invalid shape"):
        entry.configure_profile(profile, environment)
    assert environment == {"SECRET_GROQ_API_KEY": "private-test-key"}


def test_candidate_profile_is_explicit_and_installs_both_modes():
    profile = builder.profile_for("declared/model", prompt_profile="compact-v2", read_answer_mode="evidence")
    environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
    entry.configure_profile(profile, environment)
    assert environment["ACCESSFLOW_SAMSUNG_PROMPT_PROFILE"] == "compact-v2"
    assert environment["ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE"] == "evidence"
    assert builder.profile_for("declared/model")["ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE"] == "prose"


@pytest.mark.parametrize("field,value", [("ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE", "guess"),
                                       ("ACCESSFLOW_SAMSUNG_PROMPT_PROFILE", "compact-v99")])
def test_invalid_package_modes_fail_before_environment_mutation(field, value):
    profile = builder.profile_for("declared/model")
    profile[field] = value
    environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
    with pytest.raises(ValueError, match="Unsupported package"):
        entry.configure_profile(profile, environment)
    assert environment == {"SECRET_GROQ_API_KEY": "private-test-key"}


@pytest.mark.parametrize("prompt,answer", [("full", "prose"), ("compact-v2", "evidence")])
async def test_packaged_setup_delivers_profile_to_controller_and_reasoner(monkeypatch, tmp_path, prompt, answer):
    from accessflow.adapters import models

    class Backend:
        def __init__(self, provider):
            self.name = provider
            self.warmed = False

        async def warmup(self):
            self.warmed = True

    profile = builder.profile_for("declared/model", prompt_profile=prompt, read_answer_mode=answer)
    (tmp_path / "runtime_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/TOOLS.md").write_text("# Tool reference\n", encoding="utf-8")
    monkeypatch.setattr(entry, "PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(entry.os, "environ", {"SECRET_GROQ_API_KEY": "private-test-key"})
    monkeypatch.setattr(models, "JsonBackend", Backend)
    participant = entry.ParticipantAgent(asyncio.Queue(), asyncio.Queue())
    await participant.setup()
    assert participant.agent.read_answer_mode == answer
    assert participant.agent.reasoner.read_answer_mode == answer
    assert participant.agent.reasoner.prompt_profile == prompt
    assert participant.agent.reasoner.backend.warmed
    await participant.agent.perception.aclose()


@pytest.mark.parametrize("overrides", [{}, {"SECRET_GROQ_API_KEY": " "},
    {"SECRET_GROQ_API_KEY": "one", "ACCESSFLOW_GROQ_API_KEY": "two"},
    {"SECRET_GROQ_API_KEY": "one", "ACCESSFLOW_GROQ_MODEL": "different/model"}])
def test_invalid_environment_fails_without_partial_mutation_or_secret_echo(overrides):
    environment = {"UNRELATED": "retained", **overrides}
    before = dict(environment)
    with pytest.raises(ValueError) as exc:
        entry.configure_profile(builder.profile_for("declared/model"), environment)
    assert environment == before
    assert "different/model" not in str(exc.value)


def test_profile_cannot_supply_arbitrary_environment_or_endpoint():
    profile = builder.profile_for("declared/model")
    for invalid in [{**profile, "PYTHONPATH": "elsewhere"},
                    {**profile, "ACCESSFLOW_GROQ_URL": "https://elsewhere.test"}]:
        environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
        with pytest.raises(ValueError):
            entry.configure_profile(invalid, environment)
        assert environment == {"SECRET_GROQ_API_KEY": "private-test-key"}


@pytest.fixture
def package_sources(tmp_path, monkeypatch):
    repo, kit = tmp_path / "repo", tmp_path / "kit"
    for path, text in {
        repo / "src/accessflow/adapters/samsung.py": "# tracked participant\n",
        repo / "src/accessflow/untracked.py": "# must not be included\n",
        repo / "scripts/submission_entry.py": "# entry template\n",
        repo / "pyproject.toml": "[project]\n",
        repo / "uv.lock": "version = 1\n",
        repo / ".env": "SECRET_GROQ_API_KEY=not-for-package\n",
        kit / ".env": "not-for-package\n",
        kit / "agent/agent.py": "# baseline must not replace our entry\n",
        kit / "harness/runner.py": "# evaluator\n",
        kit / "harness/scorer.py": "# scorer\n",
        kit / "harness/__pycache__/old.py": "# ignored cache\n",
        kit / "docs/TOOLS.md": "# Tool interfaces\n",
        kit / "scenarios/public.json": "{}",
        kit / "audio/public.mp3": "sample",
        kit / "frames/public.png": "sample",
        **{kit / name: "# supplied kit\n" for name in builder.KIT_ROOT_FILES},
    }.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def git_output(command, **kwargs):
        assert kwargs["cwd"] == repo
        if command[:2] == ["git", "ls-files"]:
            return b"src/accessflow/adapters/samsung.py\0"
        if command == ["git", "rev-parse", "HEAD"]:
            return "a" * 40
        if command == ["git", "status", "--porcelain"]:
            return b" M scripts/build_samsung_package.py\n"
        raise AssertionError(command)

    monkeypatch.setattr(builder.subprocess, "check_output", git_output)
    return repo, kit


def test_assembly_copies_only_selected_inputs_and_records_exact_bytes(package_sources):
    repo, kit = package_sources
    output = repo / "artifacts/package"
    manifest = builder.assemble(repo, kit, output, team="Development Team", model="declared/model",
                                requirements=["pydantic==2.13.5"])
    assert manifest["source_dirty"] is True
    assert (output / "agent/agent.py").read_bytes() == (repo / "scripts/submission_entry.py").read_bytes()
    assert not (output / ".env").exists()
    assert not (output / "accessflow/untracked.py").exists()
    assert not (output / "harness/__pycache__").exists()
    assert "SECRET_GROQ_API_KEY" in (output / "submission.yaml").read_text()
    for name, digest in manifest["files"].items():
        data = (output / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        assert b"not-for-package" not in data
    assert len(manifest["files"]) == len([p for p in output.rglob("*") if p.is_file()]) - 1


def test_assembly_records_candidate_profile_and_rejects_invalid_before_creation(package_sources):
    repo, kit = package_sources
    output = repo / "artifacts/candidate"
    with pytest.raises(ValueError, match="Unsupported"):
        builder.assemble(repo, kit, output, team="Team", model="model", requirements=["thing==1"],
                         read_answer_mode="typo")
    assert not output.exists()
    builder.assemble(repo, kit, output, team="Team", model="model", requirements=["thing==1"],
                     prompt_profile="compact-v2", read_answer_mode="evidence")
    assert json.loads((output / "runtime_profile.json").read_text()) == builder.profile_for(
        "model", prompt_profile="compact-v2", read_answer_mode="evidence")


def test_assembly_never_overwrites_and_rejects_output_outside_artifacts(package_sources):
    repo, kit = package_sources
    existing = repo / "artifacts/existing"
    existing.mkdir(parents=True)
    (existing / "keep.txt").write_text("keep")
    for output in [existing, repo / "artifacts", repo.parent / "outside", repo / "src/output"]:
        with pytest.raises(ValueError, match="new package directory"):
            builder.assemble(repo, kit, output, team="Team", model="model", requirements=["thing==1"])
    assert (existing / "keep.txt").read_text() == "keep"
    assert not (repo.parent / "outside").exists()


def test_missing_kit_input_fails_before_destination_is_created(package_sources):
    repo, kit = package_sources
    (kit / "docs/TOOLS.md").unlink()
    with pytest.raises(ValueError, match="TOOLS.md"):
        builder.assemble(repo, kit, repo / "artifacts/new", team="Team", model="model",
                         requirements=["thing==1"])
    assert not (repo / "artifacts/new").exists()


def test_file_boundary_rejects_outside_file(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("outside")
    with pytest.raises(ValueError, match="boundary"):
        builder.checked_bytes(root, outside)


def test_packaged_constructor_does_not_require_keys_or_contact_a_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(entry, "PACKAGE_ROOT", tmp_path)
    monkeypatch.delenv("SECRET_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ACCESSFLOW_GROQ_API_KEY", raising=False)
    agent = entry.ParticipantAgent(asyncio.Queue(), asyncio.Queue())
    assert agent.agent is None
    assert agent.media_root == tmp_path
    assert agent.tool_documentation == "docs/TOOLS.md"
