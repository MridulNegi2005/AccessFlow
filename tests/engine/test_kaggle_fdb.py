"""Packaging guard tests; these do not pretend to execute CUDA or providers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("kaggle_runner", ROOT / "scripts/kaggle_fdb.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def archive(tmp_path, name, symlink=False):
    path = tmp_path / "inputs.zip"
    with zipfile.ZipFile(path, "w") as zipped:
        member = zipfile.ZipInfo(name)
        if symlink:
            member.external_attr = 0o120777 << 16
        zipped.writestr(member, b"fixture")
    # Windows' ZIP writer normalizes separators; represent the hostile wire name.
    if "\\" in name:
        path.write_bytes(path.read_bytes().replace(name.replace("\\", "/").encode(), name.encode()))
    return path


@pytest.mark.parametrize("name,symlink", [
    ("../outside", False), ("/outside", False), ("bad\\name", False),
    ("nested/link", True),
])
def test_archive_escape_rejected(tmp_path, monkeypatch, name, symlink):
    path = archive(tmp_path, name, symlink)
    monkeypatch.setattr(runner, "ARCHIVE_SHA", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="Unsafe archive"):
        runner.extract_corpus(path, tmp_path / "destination")
    assert not (tmp_path / "destination").exists()


def test_checksum_required_before_extraction(tmp_path):
    path = archive(tmp_path, "safe/file")
    with pytest.raises(ValueError, match="checksum"):
        runner.extract_corpus(path, tmp_path / "destination")
    assert not (tmp_path / "destination").exists()


def test_valid_archive_preserves_layout(tmp_path, monkeypatch):
    path = archive(tmp_path, "fdb_v3_data_released/example/input.wav")
    monkeypatch.setattr(runner, "ARCHIVE_SHA", hashlib.sha256(path.read_bytes()).hexdigest())
    runner.extract_corpus(path, tmp_path / "destination")
    assert (tmp_path / "destination/fdb_v3_data_released/example/input.wav").read_bytes() == b"fixture"


def test_notebook_contains_identical_runner_and_no_saved_output():
    notebook = json.loads((ROOT / "notebooks/AccessFlow_FDB_Kaggle.ipynb").read_text())
    cell = notebook["cells"][1]
    source = (ROOT / "scripts/kaggle_fdb.py").read_text().split('\nif __name__ == "__main__":')[0]
    assert "".join(cell["source"]) == source
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None
