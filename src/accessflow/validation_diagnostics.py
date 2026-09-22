"""Bounded validation telemetry containing only internal field names and enums."""

from collections.abc import Mapping
from itertools import islice

from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError as ModelValidationError

from accessflow.contracts import PlanProposal

_MAX_ERRORS = 8
_MAX_PATH = 16
_MAX_INDEX = 1_000_000
# Only this internal schema supplies printable names. In particular, properties in
# a tool's manifest or a validation exception's schema are never an allowlist.
_PLAN_SCHEMA = PlanProposal.model_json_schema()
_MODEL_CATEGORIES = {
    "missing": "missing", "extra_forbidden": "extra", "value_error": "value_error",
    "assertion_error": "value_error", "json_invalid": "invalid_json",
    "literal_error": "enum", "enum": "enum",
    **dict.fromkeys(("string_type", "int_type", "int_parsing", "int_from_float",
                     "float_type", "float_parsing", "bool_type", "bool_parsing",
                     "list_type", "dict_type", "model_type", "model_attributes_type",
                     "none_required", "json_type", "tuple_type", "set_type"), "type"),
    **dict.fromkeys(("greater_than", "greater_than_equal", "less_than", "less_than_equal",
                     "too_long", "too_short", "string_too_long", "string_too_short",
                     "string_pattern_mismatch", "finite_number", "multiple_of"), "constraint"),
}
_SCHEMA_CATEGORIES = {
    "required": "required", "type": "type", "enum": "enum", "const": "enum",
    "additionalProperties": "extra",
    **dict.fromkeys(("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                     "minLength", "maxLength", "pattern", "minItems", "maxItems",
                     "minProperties", "maxProperties", "uniqueItems", "multipleOf"),
                    "constraint"),
    **dict.fromkeys(("anyOf", "oneOf", "allOf", "not", "if", "contains"), "combination"),
}


def _resolve(node):
    if not isinstance(node, dict):
        return {}
    reference = node.get("$ref", "")
    if reference.startswith("#/$defs/"):
        return _PLAN_SCHEMA.get("$defs", {}).get(reference[len("#/$defs/"):], {})
    return node


def _path(location):
    """Walk only the trusted shape, redacting even known names used as map keys."""
    node = _PLAN_SCHEMA
    path = []
    for component in islice(location, _MAX_PATH):
        node = _resolve(node)
        properties = node.get("properties", {})
        if type(component) is int and "items" in node:
            path.append(component if 0 <= component <= _MAX_INDEX else "<index>")
            node = node.get("items", {})
        elif type(component) is str and component in properties:
            path.append(component)
            node = properties[component]
        else:
            path.append("<key>")
            node = node.get("additionalProperties", {})
    return path, _resolve(node)


def validation_summary(exc) -> dict | None:
    """Summarize recognized errors without messages, values, context or raw schemas.

    Unknown validators map to a fixed category. Paths are limited to sixteen
    components and eight errors; dynamic map keys are always replaced by <key>.
    JSON Schema context errors are deliberately not traversed or serialized.
    """
    if isinstance(exc, ModelValidationError):
        errors = []
        for error in islice(exc.errors(include_url=False, include_context=False,
                                       include_input=False), _MAX_ERRORS):
            path, _ = _path(error["loc"])
            item = {"category": _MODEL_CATEGORIES.get(error["type"], "validation"),
                    "path": path}
            if (item["category"] == "missing" and path
                    and path[-1] not in ("<key>", "<index>")
                    and isinstance(path[-1], str) and len(error["loc"]) <= _MAX_PATH):
                item["missing_field"] = path[-1]
            if len(error["loc"]) > _MAX_PATH:
                item["path_truncated"] = True
            errors.append(item)
        count = exc.error_count()
        return {"source": "pydantic", "error_count": count,
                "truncated": count > _MAX_ERRORS, "errors": errors}
    if isinstance(exc, SchemaValidationError):
        location = exc.absolute_path
        path, node = _path(location)
        category = _SCHEMA_CATEGORIES.get(exc.validator, "validation")
        item = {"category": category, "path": path}
        if len(location) > _MAX_PATH:
            item["path_truncated"] = True
        elif (category == "required" and isinstance(exc.instance, Mapping)
              and isinstance(exc.validator_value, list)):
            # Compute absent names without parsing a message that may quote input.
            missing = [field for field in node.get("properties", {})
                       if field in exc.validator_value and field not in exc.instance]
            if missing:
                item["missing_fields"] = missing[:_MAX_ERRORS]
        return {"source": "jsonschema", "error_count": 1,
                "truncated": False, "errors": [item]}
    return None
