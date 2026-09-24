"""Native package integrity; tiny fake model bytes never claim real inference."""

import hashlib
import json
from pathlib import Path
import wave

import pytest

from scripts import build_samsung_package as builder, package_media as media, submission_entry as entry
from tests.engine.test_samsung_package import package_sources  # noqa: F401


@pytest.fixture
def native(tmp_path):
    model = tmp_path / "installed"
    model.mkdir()
    hashes = {}
    for name in [*sorted(media.MODEL_REQUIRED), "vocabulary.txt"]:
        data = ("fake model fixture: " + name).encode()
        (model / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    (model / "installation_source.json").write_text(json.dumps({"repository": "fixture/model",
        "revision": "a" * 40, "files": hashes}), encoding="utf-8")
    (model / ".env").write_text("secret-test-value", encoding="utf-8")
    audio = tmp_path / "warm.wav"
    with wave.open(str(audio), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\x00\x00" * 160)
    return dict(model_dir=model, warmup_audio=audio, audio_provenance="Generated silence; package unit test only")


def materialize(root, files):
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def test_native_inputs_are_portable_bounded_and_do_not_copy_extra_files(native):
    settings, files = media.native_inputs(**native)
    assert settings["ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH"] == "assets/asr"
    assert settings["ACCESSFLOW_SAMSUNG_WARMUP_AUDIO"] == "assets/warmup.wav"
    assert settings["ACCESSFLOW_SAMSUNG_VISION_PROVIDER"] == "none"
    assert "secret-test-value" not in repr(files)
    assert str(native["model_dir"]) not in json.dumps(settings)
    record = json.loads(files["assets/installation.json"])
    assert not record["live_inference_verified"]
    assert not record["vision_service_required"]
    assert record["audio_warmup"]["sha256"] == hashlib.sha256(files["assets/warmup.wav"]).hexdigest()


@pytest.mark.parametrize("mutation", ["revision", "file_name", "hash", "missing", "model_bytes", "oversized", "origin_type"])
def test_bad_installations_fail_closed(native, monkeypatch, mutation):
    path = native["model_dir"] / "installation_source.json"
    origin = json.loads(path.read_text())
    if mutation == "revision":
        origin["revision"] = "main"
    elif mutation == "file_name":
        origin["files"]["../secret"] = "a" * 64
    elif mutation == "hash":
        origin["files"]["model.bin"] = "a" * 64
    elif mutation == "missing":
        del origin["files"]["tokenizer.json"]
    elif mutation == "model_bytes":
        (native["model_dir"] / "model.bin").write_bytes(b"changed")
    elif mutation == "oversized":
        monkeypatch.setattr(media, "MODEL_LIMIT_BYTES", 5)
    else:
        origin = []
    path.write_text(json.dumps(origin))
    with pytest.raises(ValueError):
        media.native_inputs(**native)


@pytest.mark.parametrize("change", [{"audio_provenance": ""}, {"timeout_s": float("nan")},
                                   {"vision_url": "http://localhost:11434"}, {"vision_model": "declared"}])
def test_invalid_native_options_fail_before_copy(native, change):
    with pytest.raises(ValueError):
        media.native_inputs(**{**native, **change})


def test_corrupt_warmup_wav_is_not_packaged(native):
    native["warmup_audio"].write_bytes(b"not wav")
    with pytest.raises(ValueError):
        media.native_inputs(**native)


def test_native_profile_validates_installed_paths_before_mutating_environment(native, tmp_path):
    settings, files = media.native_inputs(**native)
    profile = {**builder.profile_for("declared/model"), **settings}
    environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
    root = tmp_path / "relocated-package"
    with pytest.raises(ValueError, match="not installed"):
        entry.configure_profile(profile, environment, root=root)
    assert environment == {"SECRET_GROQ_API_KEY": "private-test-key"}
    materialize(root, files)
    entry.configure_profile(profile, environment, root=root)
    entry.configure_profile(profile, environment, root=root)
    assert environment["ACCESSFLOW_SAMSUNG_PERCEPTION"] == "process"


@pytest.mark.parametrize("value", ["../outside", "C:/machine/model", "assets/other"])
def test_package_profile_cannot_select_nonportable_paths(native, tmp_path, value):
    settings, files = media.native_inputs(**native)
    root = tmp_path / "package"
    materialize(root, files)
    profile = {**builder.profile_for("model"), **settings, "ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH": value}
    environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
    with pytest.raises(ValueError, match="packaged installation assets"):
        entry.configure_profile(profile, environment, root=root)
    assert len(environment) == 1


def test_vision_profile_is_frozen_and_records_external_service(native, tmp_path):
    image = Path(__file__).resolve().parents[1] / "fixtures/images/device_panel.png"
    settings, files = media.native_inputs(**native, vision_model="declared-vision",
         warmup_image=image, image_provenance="Existing generated device-panel development fixture")
    root = tmp_path / "package"
    materialize(root, files)
    profile = {**builder.profile_for("model"), **settings}
    environment = {"SECRET_GROQ_API_KEY": "private-test-key"}
    entry.configure_profile(profile, environment, root=root)
    assert environment["ACCESSFLOW_SAMSUNG_WARMUP_IMAGE"] == "assets/warmup.png"
    record = json.loads(files["assets/installation.json"])
    assert record["vision_service_required"] and not record["vision_weights_included"]
    environment["ACCESSFLOW_SAMSUNG_VISION_MODEL"] = "undeclared-model"
    before = dict(environment)
    with pytest.raises(ValueError, match="conflicts"):
        entry.configure_profile(profile, environment, root=root)
    assert environment == before


def test_native_assembly_includes_assets_hashes_and_requires_audio_dependencies(package_sources, native):  # noqa: F811
    repo, kit = package_sources
    output = repo / "artifacts/native"
    with pytest.raises(ValueError, match="audio dependency"):
        builder.assemble(repo, kit, output, team="Team", model="model", requirements=["httpx==1"], native=native)
    assert not output.exists()
    manifest = builder.assemble(repo, kit, output, team="Team", model="model",
        requirements=["faster-whisper==1.2.1", "av==18.1.0", "ctranslate2==4.8.2"], native=native)
    assert "assets/asr/model.bin" in manifest["files"]
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    profile = json.loads((output / "runtime_profile.json").read_text())
    env = {"SECRET_GROQ_API_KEY": "private-test-key"}
    entry.configure_profile(profile, env, root=output)
    assert env["ACCESSFLOW_SAMSUNG_PERCEPTION"] == "process"


def test_native_dependency_markers_resolve_for_explicit_targets_not_the_host():
    export = """numpy==2.4.6 ; python_full_version < '3.12'
numpy==2.5.3 ; python_full_version >= '3.12'
colorama==0.4.6 ; sys_platform == 'win32'
hf-xet==1.6.0 ; platform_machine == 'x86_64' or platform_machine == 'AMD64'
thing==1.0
"""
    assert builder.pinned_audio_requirements(export) == ["colorama==0.4.6", "hf-xet==1.6.0",
                                                       "numpy==2.4.6", "thing==1.0"]


@pytest.mark.parametrize("export", ["thing==1 ; sys_platform == 'win32'\nthing==2 ; sys_platform == 'linux'",
                                   "thing @ https://example.test/package.whl", "thing>=1", "thing[extra]==1"])
def test_native_dependency_resolution_refuses_nonportable_versions(export):
    with pytest.raises(ValueError):
        builder.pinned_audio_requirements(export)


def test_installer_pins_public_revision_and_does_not_overwrite(tmp_path):
    from scripts.install_asr_model import install
    output = tmp_path / "models/asr"
    calls = []

    def download(repo, **kwargs):
        calls.append((repo, kwargs))
        kwargs["local_dir"].mkdir(parents=True)
        for name in media.MODEL_REQUIRED | {"vocabulary.txt"}:
            (kwargs["local_dir"] / name).write_bytes(b"fake installation test")

    record = install("fixture/model", "a" * 40, output, workspace=tmp_path, downloader=download)
    assert calls[0][1]["revision"] == "a" * 40
    assert calls[0][1]["token"] is False
    assert json.loads((output / "installation_source.json").read_text()) == record
    with pytest.raises(ValueError, match="new directory"):
        install("fixture/model", "a" * 40, output, workspace=tmp_path, downloader=download)
    assert len(calls) == 1


@pytest.mark.parametrize("revision,outside", [("main", False), ("a" * 40, True)])
def test_installer_rejects_mutable_or_outside_target_before_download(tmp_path, revision, outside):
    from scripts.install_asr_model import install
    calls = []
    output = tmp_path / ("outside" if outside else "models/asr")
    with pytest.raises(ValueError):
        install("fixture/model", revision, output, workspace=tmp_path, downloader=lambda *a, **kw: calls.append(kw))
    assert not calls


def test_partial_installation_does_not_issue_a_success_record(tmp_path):
    from scripts.install_asr_model import install
    output = tmp_path / "models/asr"

    def missing(*args, **kwargs):
        output.mkdir(parents=True)
        (output / "config.json").write_text("{}")

    with pytest.raises(ValueError, match="lacks"):
        install("fixture/model", "a" * 40, output, workspace=tmp_path, downloader=missing)
    assert not (output / "installation_source.json").exists()
