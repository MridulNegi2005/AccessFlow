"""Pure, bounded selection of a delegated value from a tool result.

This module deliberately knows nothing about tools, sessions, or write
authority.  It only resolves a value from an already accepted JSON result
when exactly one collection member satisfies all declared constraints.
Pointers use RFC 6901 escaping, but this slice permits object traversal only:
array index components (including ``-``) are rejected.
"""

from __future__ import annotations

import math
import re
from typing import Any

MAX_ROWS = 256
MAX_MATCHES = 16
MAX_POINTER_DEPTH = 16
MAX_POINTER_LENGTH = 512
MAX_JSON_NODES = 4096


class BindingError(ValueError):
    """Raised when a delegated result cannot be resolved safely."""


_MISSING = object()
_NUMERIC_COMPONENT = re.compile(r"^[0-9]+$")


def _parse_pointer(pointer: str, *, name: str) -> list[str]:
    if not isinstance(pointer, str):
        raise BindingError(f"{name} must be a string JSON pointer")
    if len(pointer) > MAX_POINTER_LENGTH:
        raise BindingError(f"{name} exceeds the {MAX_POINTER_LENGTH}-character limit")
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise BindingError(f"{name} must be an absolute JSON pointer")

    components: list[str] = []
    for raw in pointer[1:].split("/"):
        # A JSON Pointer escape is exactly ~0 or ~1.  Decode after validating
        # so malformed escapes cannot be treated as ordinary object keys.
        decoded: list[str] = []
        index = 0
        while index < len(raw):
            character = raw[index]
            if character != "~":
                decoded.append(character)
                index += 1
                continue
            if index + 1 >= len(raw) or raw[index + 1] not in "01":
                raise BindingError(f"{name} contains a malformed JSON pointer escape")
            decoded.append("/" if raw[index + 1] == "1" else "~")
            index += 2
        component = "".join(decoded)
        if _NUMERIC_COMPONENT.fullmatch(component) or component == "-":
            raise BindingError(f"{name} contains an array index component")
        components.append(component)

    if len(components) > MAX_POINTER_DEPTH:
        raise BindingError(f"{name} exceeds the {MAX_POINTER_DEPTH}-component depth limit")
    return components


def _is_json_scalar(value: Any) -> bool:
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return True
    return type(value) is float and math.isfinite(value)


def _json_equal(
    left: Any,
    right: Any,
    depth: int,
    budget: list[int],
    active_left: set[int],
    active_right: set[int],
) -> bool:
    """Bounded recursive implementation for :func:`json_equal`."""

    if depth > MAX_POINTER_DEPTH or budget[0] == 0:
        return False
    budget[0] -= 1

    if type(left) is not type(right):
        return False
    if _is_json_scalar(left):
        return left == right
    if type(left) not in (list, dict) or id(left) in active_left or id(right) in active_right:
        return False

    active_left.add(id(left))
    active_right.add(id(right))
    try:
        if isinstance(left, list):
            if len(left) > budget[0]:
                return False
            return len(left) == len(right) and all(
                _json_equal(a, b, depth + 1, budget, active_left, active_right)
                for a, b in zip(left, right)
            )
        if len(left) > budget[0]:
            return False
        return (
            all(type(key) is str for key in left)
            and all(type(key) is str for key in right)
            and left.keys() == right.keys()
            and all(
                _json_equal(left[key], right[key], depth + 1, budget, active_left, active_right)
                for key in left
            )
        )
    finally:
        active_left.remove(id(left))
        active_right.remove(id(right))


def json_equal(left: Any, right: Any) -> bool:
    """Compare bounded JSON values with strict types.

    In particular, booleans never compare equal to numbers, and integers and
    floating-point numbers remain distinct (so ``1`` is not ``1.0``).  Values
    deeper than 16 levels, larger than 4096 total nodes, cyclic, non-finite,
    or otherwise unsupported are unequal.
    """

    return _json_equal(left, right, 0, [MAX_JSON_NODES], set(), set())


def _bounded_json_value(
    value: Any,
    depth: int = 0,
    budget: list[int] | None = None,
    active: set[int] | None = None,
) -> bool:
    if budget is None:
        budget = [MAX_JSON_NODES]
    if active is None:
        active = set()
    if depth > MAX_POINTER_DEPTH or budget[0] == 0:
        return False
    budget[0] -= 1
    if _is_json_scalar(value):
        return True
    if type(value) not in (list, dict) or id(value) in active:
        return False

    active.add(id(value))
    try:
        if isinstance(value, list):
            if len(value) > budget[0]:
                return False
            return all(_bounded_json_value(item, depth + 1, budget, active) for item in value)
        if len(value) > budget[0]:
            return False
        return all(
            type(key) is str and _bounded_json_value(item, depth + 1, budget, active)
            for key, item in value.items()
        )
    finally:
        active.remove(id(value))


def _read_object_path(root: Any, components: list[str]) -> Any:
    current = root
    for component in components:
        if not isinstance(current, dict) or component not in current:
            return _MISSING
        current = current[component]
    return current


def resolve_selection(
    result: dict[str, Any],
    collection_pointer: str,
    value_pointer: str,
    matches: dict[str, Any],
) -> Any:
    """Return the selected value from one uniquely matching collection row.

    ``collection_pointer`` selects a list in ``result``.  Each key in
    ``matches`` is a pointer relative to a row and its value is the expected
    JSON scalar.  Missing fields simply make that row fail its constraints;
    malformed pointers, an absent collection, no matching row, ambiguity, or
    a null selected value raise :class:`BindingError`.
    """

    if not isinstance(result, dict):
        raise BindingError("result must be a JSON object")
    if not isinstance(matches, dict) or any(type(pointer) is not str for pointer in matches):
        raise BindingError("matches must map string JSON pointers to scalar values")
    if not matches:
        raise BindingError("at least one match constraint is required")
    if len(matches) > MAX_MATCHES:
        raise BindingError(f"matches exceeds the {MAX_MATCHES}-constraint limit")
    if any(not _is_json_scalar(expected) for expected in matches.values()):
        raise BindingError("match expectations must be JSON scalar values")

    collection_path = _parse_pointer(collection_pointer, name="collection_pointer")
    value_path = _parse_pointer(value_pointer, name="value_pointer")
    match_paths = {
        pointer: _parse_pointer(pointer, name="match pointer") for pointer in matches
    }

    collection = _read_object_path(result, collection_path)
    if collection is _MISSING:
        raise BindingError("collection path is missing")
    if not isinstance(collection, list):
        raise BindingError("collection path must resolve to a list")
    if len(collection) > MAX_ROWS:
        raise BindingError(f"collection exceeds the {MAX_ROWS}-row limit")

    selected: Any = _MISSING
    matching_rows = 0
    for row in collection:
        if all(
            (candidate := _read_object_path(row, path)) is not _MISSING
            and json_equal(candidate, matches[pointer])
            for pointer, path in match_paths.items()
        ):
            matching_rows += 1
            selected = row

    if matching_rows == 0:
        raise BindingError("no collection row matches the declared constraints")
    if matching_rows != 1:
        raise BindingError("declared constraints match multiple collection rows")

    value = _read_object_path(selected, value_path)
    if value is _MISSING:
        raise BindingError("selected value path is missing")
    if value is None:
        raise BindingError("selected value must not be null")
    if not _bounded_json_value(value):
        raise BindingError("selected value is not bounded valid JSON")
    return value
