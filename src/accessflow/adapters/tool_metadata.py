"""Bounded, explicitly configured documentation evidence for tool planning.

The returned text is untrusted interface documentation, never user authority or
an observed tool result. This loader does no discovery and follows no document
links; callers must keep the evidence separate from system instructions.
"""

import hashlib
import re
from pathlib import Path, PurePosixPath


MAX_DOCUMENT_BYTES = 32768


def select_return_documentation(document: dict, tool_names: set[str]) -> dict:
    """Select verbatim success examples for named runtime tools when available.

    This is format-based reference selection, not schema inference. Unrecognized
    formats retain the full bounded reference; fields and examples are not invented.
    """
    lines = document["text"].splitlines()
    sections = {}
    active = None
    heading = None
    for index, line in enumerate(lines, 1):
        match = re.match(r"^###\s+`([^`]+)`(?:\s|$)", line)
        if match:
            active, heading = match.group(1), index
        elif line.startswith("#"):
            active = None
        elif active in tool_names and line.startswith("Success:"):
            sections.setdefault(active, []).extend([heading, index])
    # Tools without an example retain only their runtime argument manifest;
    # never invent a return layout or imply this excerpt is complete documentation.
    if not sections:
        return dict(document)
    indices = sorted({n for entries in sections.values() for n in entries})
    text = "\n".join(lines[n - 1] for n in indices)
    return {**document, "text": text, "selection": "verbatim_success_lines",
            "included_line_numbers": indices,
            "excerpt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def load_tool_documentation(kit_root: Path, relative_path: str) -> dict:
    """Read one UTF-8 Markdown file beneath the selected kit's docs directory.

    Invalid configuration raises ValueError before a caller starts inference.
    Source paths are relative to the resolved kit root; hashes cover the exact
    bytes read, including original line endings. Empty documents have zero lines.
    """
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("Tool documentation must name a relative Markdown file below kit/docs")
    if any(character in relative_path for character in ("\\", ":", "\x00")):
        raise ValueError("Tool documentation path contains a forbidden character")
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Tool documentation path must not be absolute or contain parent traversal")
    if len(path.parts) < 2 or path.parts[0] != "docs" or path.suffix.lower() != ".md":
        raise ValueError("Tool documentation must be a Markdown file below kit/docs")

    try:
        root = Path(kit_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Tool documentation kit root must be a directory")
        candidate = root.joinpath(*path.parts).resolve(strict=True)
        # Do not resolve docs separately: a docs symlink must not redefine the
        # allowed subtree to point outside the kit or at a different kit folder.
        if not candidate.is_relative_to(root / "docs"):
            raise ValueError("Tool documentation resolves outside kit/docs")
        if candidate.suffix.lower() != ".md" or not candidate.is_file():
            raise ValueError("Tool documentation must resolve to a regular Markdown file")
        with candidate.open("rb") as handle:
            raw = handle.read(MAX_DOCUMENT_BYTES + 1)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Tool documentation file cannot be resolved or read") from exc

    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"Tool documentation exceeds {MAX_DOCUMENT_BYTES} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("Tool documentation must use valid UTF-8") from exc

    return {
        "source": candidate.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "encoding": "utf-8",
        "byte_count": len(raw),
        "line_start": 1,
        "line_end": len(text.splitlines()),
        "text": text,
    }
