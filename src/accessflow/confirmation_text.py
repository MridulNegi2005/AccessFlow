"""Literal, bounded wording for effects already confirmed by the controller.

Formatting is never authority to confirm an effect. Call only after the existing
commit/reconciliation gates, and retain the original result alongside this text.
"""

import json
import math
import re

MAX_FIELDS = 12
MAX_CHARS = 1200
MAX_DEPTH = 4


class PresentationError(ValueError):
    pass


def confirmation_payload(result, *, reconciled=False, effect_environment="unspecified"):
    # Only trusted runtime configuration supplies provenance; never inspect model
    # prose, tool names or result fields to decide whether an effect is simulated.
    environment = "mock" if effect_environment == "mock" else "unspecified"
    noun = "mock action" if environment == "mock" else "action"
    prefix = f"The status check confirms the {noun}." if reconciled else f"The {noun} is confirmed."
    pieces = []
    length = len(prefix)

    def label(key):
        if not isinstance(key, str) or len(key) > 80 or any(ord(c) < 32 for c in key):
            raise PresentationError("invalid_label")
        display = key.replace("_", " ")
        if re.fullmatch(r"[\w -]+", display):
            words = [word.upper() if word.lower() == "id" else word for word in display.split(" ")]
            display = " ".join(words)
            return display[:1].upper() + display[1:]
        return json.dumps(display, ensure_ascii=False)

    def leaf(value, path):
        nonlocal length
        if isinstance(value, str) and len(value) > 240:
            raise PresentationError("too_large")
        if isinstance(value, float) and not math.isfinite(value):
            raise PresentationError("unsupported_value")
        if isinstance(value, int) and value.bit_length() > 1024:
            raise PresentationError("too_large")
        if isinstance(value, dict) and not value:
            encoded = "empty object"
        elif isinstance(value, list) and not value:
            encoded = "empty list"
        elif value is None or isinstance(value, (str, bool, int, float)):
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        else:
            raise PresentationError("unsupported_value")
        text = f"{', '.join(path)}: {encoded}."
        length += 1 + len(text)
        if len(pieces) >= MAX_FIELDS or length > MAX_CHARS:
            raise PresentationError("too_large")
        pieces.append(text)

    def visit(value, path, depth):
        if depth > MAX_DEPTH:
            raise PresentationError("too_deep")
        if isinstance(value, dict) and value:
            for key, child in value.items():
                visit(child, [*path, label(key)], depth + 1)
        elif isinstance(value, list) and value:
            for i, child in enumerate(value):
                visit(child, [*path, f"item {i + 1}"], depth + 1)
        else:
            leaf(value, path)

    try:
        if not isinstance(result, dict):
            raise PresentationError("unsupported_value")
        if result:
            visit(result, [], 0)
    except PresentationError as exc:
        # No partly rendered fields: do not silently drop a possible qualifier.
        return {"text": prefix + " I couldn't summarize the returned details.",
                "effect_environment": environment,
                "result_presentation": {"status": "omitted", "reason": str(exc)}}
    return {"text": " ".join([prefix, *pieces]), "effect_environment": environment,
            "result_presentation": {"status": "complete"}}
