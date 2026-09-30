"""Saved output restoration validates real files before any writes."""

import json
import hashlib
import wave

import pytest

from scripts import reproduce_fdb as fdb
from scripts import restore_fdb_evidence as restoration


@pytest.fixture
def recording_bundle(tmp_path, monkeypatch):
    reference, evidence = tmp_path / "reference", tmp_path / "evidence"
    reference.mkdir()
    evidence.mkdir()
    hashes = {}
    for name in fdb.REQUIRED:
        path = reference / name
        path.write_text("unchanged reference fixture\n")
        hashes[name] = fdb.digest(path)
    inputs, retained = [], []
    for i in range(100):
        folder = f"example_{i:03d}_{i:024x}"
        target = reference / "fdb_v3_data_released" / folder
        target.mkdir(parents=True)
        audio = target / "input.wav"
        with wave.open(str(audio), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(48000)
            out.writeframes(b"\0\0" * 48)
        (target / "metadata.json").write_text("{}")
        inputs.append({"folder": folder, "sha256": fdb.digest(audio)})
        result = evidence / "results" / folder / "result_accessflow.json"
        result.parent.mkdir(parents=True)
        result.write_text('{"status":"completed"}')
        retained.append({"path": result.relative_to(evidence).as_posix(), "sha256": fdb.digest(result)})
    manifest = {
        "fdb_commit": fdb.PIN,
        "agent_commit": "recorded-commit",
        "source_sha256": hashes,
        "inputs": inputs,
        "retained_outputs": retained,
        "results": {"expected": 100, "missing": [], "status_counts": {"completed": 100}},
    }
    manifest_path = evidence / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(fdb, "git_output", lambda path, *args: fdb.PIN if args[0] == "rev-parse" else "")
    return reference, evidence, manifest


def save(evidence, manifest):
    (evidence / "manifest.json").write_text(json.dumps(manifest))


def test_restore_all_recordings_and_repeat_without_overwrite(recording_bundle):
    reference, evidence, _ = recording_bundle
    first = restoration.restore(evidence, reference)
    assert first["recordings"] == first["files_copied"] == 100
    assert first["status"] == "recorded_outputs_restored_not_scored"
    assert len(list(reference.rglob("result_accessflow.json"))) == 100
    second = restoration.restore(evidence, reference)
    assert second["files_copied"] == 0 and second["already_present"] == 100


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"])
def test_same_pinned_text_restores_across_checkout_line_endings(recording_bundle, line_ending):
    reference, evidence, manifest = recording_bundle
    for name in fdb.REQUIRED:
        path = reference / name
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        recorded = raw.replace(b"\n", b"\r\n" if line_ending == b"\n" else b"\n")
        manifest["source_sha256"][name] = hashlib.sha256(recorded).hexdigest()
        path.write_bytes(raw.replace(b"\n", line_ending))
    save(evidence, manifest)
    assert restoration.restore(evidence, reference)["files_copied"] == 100


@pytest.mark.parametrize(
    "fault",
    [
        "corrupt_output",
        "changed_audio",
        "changed_source",
        "wrong_pin",
        "duplicate",
        "missing",
        "escape",
        "conflict",
    ],
)
def test_invalid_bundle_does_not_partially_restore(recording_bundle, fault):
    reference, evidence, manifest = recording_bundle
    row = manifest["retained_outputs"][-1]
    source = evidence / row["path"]
    audio = reference / "fdb_v3_data_released" / manifest["inputs"][-1]["folder"] / "input.wav"
    if fault == "corrupt_output":
        source.write_text("corrupted")
    elif fault == "changed_audio":
        audio.write_bytes(audio.read_bytes() + b"x")
    elif fault == "changed_source":
        (reference / fdb.REQUIRED[0]).write_text("changed")
    elif fault == "wrong_pin":
        manifest["fdb_commit"] = "wrong"
    elif fault == "duplicate":
        manifest["retained_outputs"].append(row)
    elif fault == "missing":
        manifest["retained_outputs"].pop()
    elif fault == "escape":
        row["path"] = "results/../outside.json"
    elif fault == "conflict":
        (audio.parent / "result_accessflow.json").write_text("original target")
    save(evidence, manifest)
    with pytest.raises(ValueError):
        restoration.restore(evidence, reference)
    existing = list(reference.rglob("result_accessflow.json"))
    assert len(existing) == (1 if fault == "conflict" else 0)
    if existing:
        assert existing[0].read_text() == "original target"


def test_manifest_counts_cannot_hide_a_failed_recording(recording_bundle):
    reference, evidence, manifest = recording_bundle
    row = manifest["retained_outputs"][-1]
    source = evidence / row["path"]
    source.write_text('{"status":"inference_failed"}')
    row["sha256"] = fdb.digest(source)
    save(evidence, manifest)
    with pytest.raises(ValueError, match="coverage/statuses"):
        restoration.restore(evidence, reference)
    assert not list(reference.rglob("result_accessflow.json"))
    manifest["results"]["status_counts"] = {"completed": 99, "inference_failed": 1}
    save(evidence, manifest)
    assert restoration.restore(evidence, reference)["result_status_counts"]["inference_failed"] == 1


def test_cli_bad_manifest_has_safe_error(tmp_path, capsys):
    (tmp_path / "manifest.json").write_text("[]")
    with pytest.raises(SystemExit) as error:
        restoration.main(["--evidence", str(tmp_path), "--fdb-root", str(tmp_path)])
    assert error.value.code == 1
    assert "ValueError" in capsys.readouterr().err
