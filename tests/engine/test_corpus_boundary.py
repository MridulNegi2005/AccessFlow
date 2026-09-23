"""Bounded corpus reads and sanitized resolution failures; no live model involved."""

from pathlib import Path

import pytest

from accessflow.corpus import CorpusAccessError, CorpusStore


def test_file_growth_after_size_check_is_bounded_and_refused(tmp_path, monkeypatch):
    document = tmp_path / "manual.txt"
    document.write_bytes(b"small")
    store = CorpusStore(tmp_path, max_document_bytes=16)
    original_open = Path.open
    read_sizes = []

    class ObservedRead:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, size=-1):
            read_sizes.append(size)
            return self.stream.read(size)

    def grow_before_open(path, *args, **kwargs):
        if path == document:
            with original_open(path, "wb") as writer:
                writer.write(b"x" * 4096)
            return ObservedRead(original_open(path, *args, **kwargs))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", grow_before_open)
    with pytest.raises(CorpusAccessError, match="document_too_large"):
        store.read("manual.txt", {"manual.txt"})
    assert read_sizes == [17], "read at most the byte limit plus one overflow sentinel"


@pytest.mark.parametrize("failure", [PermissionError, OSError, RuntimeError])
def test_resolution_failure_is_sanitized(tmp_path, monkeypatch, failure):
    store = CorpusStore(tmp_path)
    original_resolve = Path.resolve

    def broken_resolution(path, *args, **kwargs):
        if path.name == "manual.txt":
            raise failure(f"private filesystem detail: {tmp_path}")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", broken_resolution)
    with pytest.raises(CorpusAccessError) as caught:
        store.read("manual.txt", {"manual.txt"})
    assert caught.value.code == "document_unreadable"
    assert str(caught.value) == "document_unreadable"
    assert caught.value.__suppress_context__


def test_resolved_escape_is_rejected_before_open(tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside evidence", encoding="utf-8")
    store = CorpusStore(root)
    original_resolve = Path.resolve

    def escaped_resolution(path, *args, **kwargs):
        if path == root / "manual.txt":
            return outside
        return original_resolve(path, *args, **kwargs)

    def forbidden_open(*args, **kwargs):
        raise AssertionError("escaped path must not be opened")

    monkeypatch.setattr(Path, "resolve", escaped_resolution)
    monkeypatch.setattr(Path, "open", forbidden_open)
    with pytest.raises(CorpusAccessError, match="unsafe_document_name"):
        store.read("manual.txt", {"manual.txt"})


def test_native_symlink_escape_when_supported(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside evidence", encoding="utf-8")
    try:
        (root / "manual.txt").symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Native symlink unavailable: {type(exc).__name__}")
    with pytest.raises(CorpusAccessError, match="unsafe_document_name"):
        CorpusStore(root).read("manual.txt", {"manual.txt"})


@pytest.mark.parametrize("raw, expected", [
    (b"", ""),
    (b"a\xffb", "a\ufffdb"),
    (b"a\r\nb\rc\n", "a\nb\nc\n"),
    ("é".encode("utf-8") * 4, "é" * 4),
])
def test_byte_bounded_read_preserves_decoding_and_newline_behavior(tmp_path, raw, expected):
    (tmp_path / "manual.txt").write_bytes(raw)
    assert CorpusStore(tmp_path, max_document_bytes=8).read("manual.txt", {"manual.txt"}) == expected


@pytest.mark.parametrize("invalid", [-1, 0, True, 1.5, float("inf"), None, "16"])
def test_invalid_read_budget_rejected_at_configuration(tmp_path, invalid):
    with pytest.raises(ValueError, match="positive integer"):
        CorpusStore(tmp_path, max_document_bytes=invalid)
