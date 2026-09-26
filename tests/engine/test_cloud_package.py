"""Cloud media package declares both models and only installation fixtures."""

import json
import wave
from pathlib import Path

import pytest

from accessflow.adapters.configured_agent import PerceptionConfig
from scripts import build_samsung_package as builder, package_media as media, submission_entry as entry
from tests.engine.test_samsung_package import package_sources  # noqa: F401


def cloud_sources(tmp_path):
    audio = tmp_path / "warm.wav"
    with wave.open(str(audio), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x00" * 160)
    image = Path(__file__).resolve().parents[1] / "fixtures/images/device_panel.png"
    return dict(warmup_audio=audio, warmup_image=image,
                audio_provenance="Generated installation WAV for contract testing",
                image_provenance="Development PNG for contract testing")


def test_cloud_profile_requires_both_models_and_rejects_local_paths(tmp_path):
    settings, files = media.cloud_inputs(**cloud_sources(tmp_path))
    root = tmp_path / "package"
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    profile = {**builder.profile_for("qwen/qwen3.8-27b"), **settings}
    config = PerceptionConfig.from_environment(root, profile)
    assert config.mode == "cloud"
    assert config.asr_model == "whisper-large-v3-turbo"
    assert config.vision_model == "qwen/qwen3.8-27b"
    environment = {"SECRET_GROQ_API_KEY": "fixture-private-key"}
    entry.configure_profile(profile, environment, root=root)
    assert environment["ACCESSFLOW_GROQ_API_KEY"] == "fixture-private-key"
    assert "fixture-private-key" not in json.dumps(profile)
    for change in ({"ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH": "assets/asr"},
                   {"ACCESSFLOW_SAMSUNG_VISION_URL": "http://localhost:11434"}):
        with pytest.raises(ValueError):
            PerceptionConfig.from_environment(root, {**profile, **change})
    for name, path in (("ACCESSFLOW_SAMSUNG_WARMUP_AUDIO", "../outside.wav"),
                       ("ACCESSFLOW_SAMSUNG_WARMUP_IMAGE", "assets/other.png")):
        with pytest.raises(ValueError, match="packaged warm-up"):
            entry.configure_profile({**profile, name: path}, {"SECRET_GROQ_API_KEY": "fixture"}, root=root)


def test_cloud_package_has_no_model_weights_and_is_hashable(package_sources, tmp_path):  # noqa: F811
    repo, kit = package_sources
    output = repo / "artifacts/cloud"
    manifest = builder.assemble(repo, kit, output, team="Team", model="qwen/qwen3.8-27b",
                                requirements=["httpx==0.28.1"], cloud=cloud_sources(tmp_path))
    assert (output / "assets/warmup.wav").is_file()
    assert (output / "assets/warmup.png").is_file()
    assert not (output / "assets/asr").exists()
    assert "assets/installation.json" in manifest["files"]
    record = json.loads((output / "assets/installation.json").read_text())
    assert record["mode"] == "cloud"
    assert not record["local_weights_included"]
    assert not record["live_inference_verified"]
    assert json.loads((output / "runtime_profile.json").read_text())[
        "ACCESSFLOW_SAMSUNG_PERCEPTION"] == "cloud"
    assert (output / "submission.yaml").read_text().count("SECRET_GROQ_API_KEY") == 1


def test_cloud_and_native_media_are_mutually_exclusive(package_sources, tmp_path):  # noqa: F811
    repo, kit = package_sources
    with pytest.raises(ValueError, match="either native or cloud"):
        builder.assemble(repo, kit, repo / "artifacts/cloud", team="Team", model="model",
                         requirements=["httpx==0.28.1"], native={}, cloud=cloud_sources(tmp_path))
    assert not (repo / "artifacts/cloud").exists()
