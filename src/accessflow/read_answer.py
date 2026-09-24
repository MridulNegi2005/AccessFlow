"""Bounded, literal read-result presentation; no model-authored factual prose.

This establishes provenance/fidelity, not source truth, relevance or completeness.
Read-only JSON pointers deliberately support arrays, unlike write-selection rules.
"""

import json
import math
import re

READ_ANSWER_MODES = frozenset({"prose", "evidence"})
MAX_FIELDS = 48
MAX_CHARS = 6000
MAX_DEPTH = 8


class ReadAnswerError(ValueError):
    """Fixed diagnostics must not echo model or tool contents."""


def has_read_attempt(view):
    return any(c.effect == "read" and c.request_id == view.active_request_id for c in view.calls)


def accepted_reads(view):
    calls = {c.call_id: c for c in view.calls if c.effect == "read" and c.status == "success"
             and c.request_id == view.active_request_id
             and all(k in view.state.slots and view.state.slots[k].revision == rev
                     for k, rev in c.dependencies.items())}
    results = {}
    for result in view.results:
        if result.status == "success" and result.call_id in calls:
            if result.call_id in results:
                raise ReadAnswerError("duplicate_read_evidence")
            results[result.call_id] = result.result
    return results


def resolve_pointer(value, pointer):
    if not pointer:
        return value, []
    if not pointer.startswith("/"):
        raise ReadAnswerError("invalid_read_pointer")
    parts = pointer[1:].split("/")
    if len(parts) > MAX_DEPTH:
        raise ReadAnswerError("read_answer_too_deep")
    path = []
    for part in parts:
        if re.search(r"~(?![01])", part):
            raise ReadAnswerError("invalid_read_pointer")
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and part in value:
            value = value[part]
            path.append(part)
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", part):
            # Bound before int conversion, including attacker-supplied huge indices.
            if len(part) > 8 or int(part) >= len(value):
                raise ReadAnswerError("missing_read_pointer")
            value = value[int(part)]
            path.append(f"Item {int(part) + 1}")
        else:
            raise ReadAnswerError("missing_read_pointer")
    return value, path


def _label(key):
    if not isinstance(key, str) or len(key) > 160 or any(ord(c) < 32 for c in key):
        raise ReadAnswerError("unsupported_read_label")
    # Quoting preserves punctuation/control boundaries; only underscores are display
    # separators. No inferred currency, billing period, totals or field semantics.
    display = key.replace("_", " ")
    if re.fullmatch(r"[\w -]+", display):
        return display[:1].upper() + display[1:]
    return json.dumps(display, ensure_ascii=False)


def render_answer(answer, view):
    results = accepted_reads(view)
    blocks, sources, seen = [], [], set()
    fields = chars = 0

    def line(label, value):
        nonlocal fields, chars
        if not (value is None or isinstance(value, (str, bool, int, float)) or value == {} or value == []):
            raise ReadAnswerError("unsupported_read_value")
        if isinstance(value, float) and not math.isfinite(value):
            raise ReadAnswerError("unsupported_read_value")
        if isinstance(value, int) and value.bit_length() > 12000:
            # Stay below Python's decimal conversion limit even for directly
            # constructed ToolResult objects; reject rather than crash rendering.
            raise ReadAnswerError("read_answer_too_large")
        if isinstance(value, str) and len(value) > MAX_CHARS:
            raise ReadAnswerError("read_answer_too_large")
        text = f"{label}: {json.dumps(value, ensure_ascii=False, allow_nan=False)}"
        fields += 1
        chars += len(text)
        if fields > MAX_FIELDS or chars > MAX_CHARS:
            raise ReadAnswerError("read_answer_too_large")
        return text

    def walk(value, path, depth):
        if depth > MAX_DEPTH:
            raise ReadAnswerError("read_answer_too_deep")
        label = " / ".join(path) or "Result"
        if isinstance(value, dict):
            if not value:
                return [line(label, {})]
            return [text for key, child in value.items()
                    for text in walk(child, [*path, _label(key)], depth + 1)]
        if isinstance(value, list):
            if not value:
                return [line(label, [])]
            return [text for i, child in enumerate(value)
                    for text in walk(child, [*path, f"Item {i + 1}"], depth + 1)]
        return [line(label, value)]

    for selection in answer.selections:
        key = (selection.call_id, selection.pointer)
        if key in seen:
            raise ReadAnswerError("duplicate_read_selection")
        seen.add(key)
        if selection.call_id not in results:
            raise ReadAnswerError("unavailable_read_evidence")
        value, path = resolve_pointer(results[selection.call_id], selection.pointer)
        heading = f"Result {len(blocks) + 1}"
        if path:
            heading += " — " + " / ".join(_label(p) for p in path)
        lines = walk(value, [], len(path))
        blocks.append(heading + "\n" + "\n".join(lines))
        sources.append(selection.model_dump())
    text = "Selected lookup fields:\n" + "\n\n".join(blocks)
    if len(text) > MAX_CHARS:
        raise ReadAnswerError("read_answer_too_large")
    return text, sources
