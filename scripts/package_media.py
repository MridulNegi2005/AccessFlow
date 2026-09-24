"""Explicit installation assets for a local Samsung package, never scenario labels."""

import hashlib
import json
from pathlib import Path
import re

from accessflow.adapters.configured_agent import PerceptionConfig
from accessflow.perception.local import validate_png, validate_wav


MODEL_REQUIRED = {"config.json", "model.bin", "tokenizer.json"}
MODEL_OPTIONAL = {"vocabulary.json", "vocabulary.txt", "preprocessor_config.json", "README.md", "LICENSE", "LICENSE.txt"}
MODEL_LIMIT_BYTES = 512 * 1024 * 1024


def native_inputs(*, model_dir, warmup_audio, audio_provenance, timeout_s=30,
                  vision_model=None, vision_url=None, warmup_image=None, image_provenance=None):
    """Return frozen settings and selected bytes from explicitly named inputs.

    The model installation record pins a repository revision and exact hashes.
    Extra cache files, credentials and unrelated recordings are never copied.
    This checks packaging integrity; setup must still load the real models.
    """
    model_dir, warmup_audio = Path(model_dir), Path(warmup_audio)
    if model_dir.is_symlink() or not model_dir.is_dir():
        raise ValueError("ASR source must be an installed regular directory")
    origin_path = model_dir / "installation_source.json"
    if origin_path.is_symlink() or not origin_path.is_file() or origin_path.stat().st_size > 65536:
        raise ValueError("ASR installation_source.json is missing or invalid")
    try:
        origin = json.loads(origin_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ValueError("Invalid ASR installation record") from exc
    if (not isinstance(origin, dict) or set(origin) != {"repository", "revision", "files"}
            or not isinstance(origin["repository"], str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", origin["repository"])
            or not isinstance(origin["revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", origin["revision"])
            or not isinstance(origin["files"], dict)):
        raise ValueError("ASR installation record requires repository, immutable revision and file hashes")
    declared = origin["files"]
    if (not MODEL_REQUIRED <= declared.keys() or not declared.keys() <= MODEL_REQUIRED | MODEL_OPTIONAL
            or not any(name in declared for name in ("vocabulary.json", "vocabulary.txt"))):
        raise ValueError("ASR installation record has missing or unsupported files")
    files = {}
    size = 0
    for name, digest in declared.items():
        path = model_dir / name
        if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(model_dir.resolve())):
            raise ValueError("Invalid ASR model file or digest")
        size += path.stat().st_size
        if size > MODEL_LIMIT_BYTES:
            raise ValueError("ASR model exceeds the package size bound")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"ASR installation hash mismatch: {name}")
        files[f"assets/asr/{name}"] = data

    def fixture(path, provenance, validator, target):
        if not isinstance(provenance, str) or not provenance.strip() or len(provenance) > 2000:
            raise ValueError("Each warm-up fixture requires explicit bounded provenance")
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Warm-up fixture must be a regular file")
        validator(path)
        files[target] = path.read_bytes()
        return {"path": target, "provenance": provenance, "sha256": hashlib.sha256(files[target]).hexdigest()}

    audio_record = fixture(warmup_audio, audio_provenance, validate_wav, "assets/warmup.wav")
    # Validate source-side configuration using the same parser as setup.
    settings = {"ACCESSFLOW_SAMSUNG_PERCEPTION": "process",
                "ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH": str(model_dir.resolve()),
                "ACCESSFLOW_SAMSUNG_WARMUP_AUDIO": str(warmup_audio.resolve()),
                "ACCESSFLOW_SAMSUNG_PERCEPTION_TIMEOUT_S": str(timeout_s),
                "ACCESSFLOW_SAMSUNG_VISION_PROVIDER": "ollama" if vision_model else "none"}
    image_record = None
    if vision_model:
        if warmup_image is None:
            raise ValueError("Vision requires a warm-up PNG")
        image_record = fixture(warmup_image, image_provenance, validate_png, "assets/warmup.png")
        settings.update({"ACCESSFLOW_SAMSUNG_VISION_MODEL": vision_model,
                         "ACCESSFLOW_SAMSUNG_VISION_URL": vision_url or "http://127.0.0.1:11434",
                         "ACCESSFLOW_SAMSUNG_WARMUP_IMAGE": str(Path(warmup_image).resolve())})
    elif any(value is not None for value in (vision_url, warmup_image, image_provenance)):
        raise ValueError("Vision inputs require an explicit vision model")
    PerceptionConfig.from_environment(Path.cwd(), settings)
    settings["ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH"] = "assets/asr"
    settings["ACCESSFLOW_SAMSUNG_WARMUP_AUDIO"] = "assets/warmup.wav"
    if image_record:
        settings["ACCESSFLOW_SAMSUNG_WARMUP_IMAGE"] = "assets/warmup.png"
    record = {"asr": origin, "audio_warmup": audio_record, "image_warmup": image_record,
              "vision_weights_included": False,
              "vision_service_required": bool(vision_model), "live_inference_verified": False}
    files["assets/installation.json"] = (json.dumps(record, indent=2) + "\n").encode()
    return settings, files
