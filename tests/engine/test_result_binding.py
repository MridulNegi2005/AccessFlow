import pytest

from accessflow.result_binding import BindingError, json_equal, resolve_selection


def test_resolves_unique_generic_row_with_escaped_pointers():
    result = {
        "payload": {
            "items": [
                {"id": "wrong", "meta/name": "other", "start": "10:00"},
                {"id": "chosen", "meta/name": "requested", "start": "11:30"},
            ]
        }
    }

    assert resolve_selection(
        result,
        "/payload/items",
        "/id",
        {"/meta~1name": "requested", "/start": "11:30"},
    ) == "chosen"


def test_typed_json_equality_keeps_booleans_and_numbers_distinct():
    result = {"rows": [{"id": "truth", "active": True}, {"id": "one", "active": 1}]}

    assert resolve_selection(result, "/rows", "/id", {"/active": True}) == "truth"
    assert resolve_selection(result, "/rows", "/id", {"/active": 1}) == "one"
    assert json_equal(True, 1) is False
    assert json_equal(1, 1.0) is False


@pytest.mark.parametrize(
    ("result", "collection_pointer", "value_pointer", "matches"),
    [
        (
            {"rows": [{"id": "a", "value": "one"}, {"id": "a", "value": "two"}]},
            "/rows",
            "/value",
            {"/id": "a"},
        ),
        ({"rows": [{"id": "a"}]}, "/rows", "/id", {"/missing": "x"}),
        ({"rows": [{"id": None}]}, "/rows", "/id", {"/id": None}),
        ({"rows": [{"id": "a"}]}, "/rows", "/missing", {"/id": "a"}),
        ({"rows": {"id": "a"}}, "/rows", "/id", {"/id": "a"}),
        ({"other": []}, "/rows", "/id", {"/id": "a"}),
    ],
)
def test_rejects_ambiguous_missing_null_and_non_collection_results(
    result, collection_pointer, value_pointer, matches
):
    with pytest.raises(BindingError):
        resolve_selection(result, collection_pointer, value_pointer, matches)


@pytest.mark.parametrize(
    ("collection_pointer", "value_pointer", "matches"),
    [
        ("rows", "/id", {"/id": "a"}),
        ("/rows/0", "/id", {"/id": "a"}),
        ("/rows", "id", {"/id": "a"}),
        ("/rows", "/id/0", {"/id": "a"}),
        ("/rows", "/id", {"/when~2": "today"}),
        ("/rows", "/id", {"/0": "today"}),
        ("/rows", "/id", {"/nested/-": "today"}),
    ],
)
def test_rejects_malformed_or_index_pointers(collection_pointer, value_pointer, matches):
    with pytest.raises(BindingError):
        resolve_selection({"rows": [{"id": "a"}]}, collection_pointer, value_pointer, matches)


def test_rejects_pointer_depth_length_and_row_limits():
    deep_pointer = "/" + "/".join(f"level{index}" for index in range(17))
    long_pointer = "/" + "x" * 512

    with pytest.raises(BindingError):
        resolve_selection({"rows": [{"id": "a"}]}, deep_pointer, "/id", {"/id": "a"})
    with pytest.raises(BindingError):
        resolve_selection({"rows": [{"id": "a"}]}, "/rows", long_pointer, {"/id": "a"})
    with pytest.raises(BindingError):
        resolve_selection(
            {"rows": [{"id": str(index)} for index in range(257)]},
            "/rows",
            "/id",
            {"/id": "0"},
        )


def test_rejects_non_scalar_match_expectation():
    with pytest.raises(BindingError):
        resolve_selection({"rows": [{"id": "a"}]}, "/rows", "/id", {"/id": ["a"]})


def _nested_list(depth):
    value = "leaf"
    for _ in range(depth):
        value = [value]
    return value


def test_requires_a_bounded_number_of_constraints():
    with pytest.raises(BindingError):
        resolve_selection({"rows": [{"id": "a"}]}, "/rows", "/id", {})
    with pytest.raises(BindingError):
        resolve_selection(
            {"rows": [{"id": "a"}]},
            "/rows",
            "/id",
            {f"/constraint{index}": "x" for index in range(17)},
        )


def test_json_equal_rejects_depth_node_and_cycle_overruns():
    assert json_equal(_nested_list(16), _nested_list(16)) is True
    assert json_equal(_nested_list(17), _nested_list(17)) is False

    large = list(range(4095))
    assert json_equal(large, list(large)) is True
    too_large = list(range(4096))
    assert json_equal(too_large, list(too_large)) is False
    large_object = {f"key{index}": index for index in range(4095)}
    assert json_equal(large_object, dict(large_object)) is True
    too_large_object = {f"key{index}": index for index in range(4096)}
    assert json_equal(too_large_object, dict(too_large_object)) is False

    cyclic_left = []
    cyclic_left.append(cyclic_left)
    cyclic_right = []
    cyclic_right.append(cyclic_right)
    assert json_equal(cyclic_left, cyclic_right) is False


@pytest.mark.parametrize(
    "selected",
    [
        float("inf"),
        object(),
        _nested_list(17),
        list(range(4097)),
        {1: "non-string JSON object key"},
    ],
)
def test_rejects_unbounded_or_unsupported_selected_values(selected):
    with pytest.raises(BindingError):
        resolve_selection(
            {"rows": [{"id": "target", "value": selected}]},
            "/rows",
            "/value",
            {"/id": "target"},
        )


def test_returns_bounded_generic_json_selected_value():
    selected = {"items": ["one", 2, False], "label": "chosen"}

    assert resolve_selection(
        {"rows": [{"id": "target", "value": selected}]},
        "/rows",
        "/value",
        {"/id": "target"},
    ) == selected


def test_rejects_cyclic_selected_value():
    cyclic = {"self": None}
    cyclic["self"] = cyclic

    with pytest.raises(BindingError):
        resolve_selection(
            {"rows": [{"id": "target", "value": cyclic}]},
            "/rows",
            "/value",
            {"/id": "target"},
        )
