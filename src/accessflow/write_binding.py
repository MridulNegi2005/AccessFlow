"""Precommitted argument provenance; this does not establish write permission."""

from dataclasses import dataclass

from jsonschema import Draft202012Validator

from .contracts import WriteContract
from .result_binding import BindingError, json_equal, resolve_selection


@dataclass
class BoundWrite:
    contract: WriteContract
    request_id: str
    input_epoch: int
    intent: str | None
    revisions: dict[str, int]


def capture(contract, *, proposal_calls, dispatched, ledger, manifests, state,
            origins, request_id, input_epoch):
    """Bind only explicit reads and already user-fixed slots, before their results."""
    target = manifests.get(contract.tool)
    if not target or target.effect != "write" or not contract.delegated_arguments:
        raise BindingError("invalid write target")
    fixed, delegated = contract.fixed_arguments, contract.delegated_arguments
    properties = target.parameters.get("properties", {})
    if len(fixed) + len(delegated) > 32 or set(fixed) & set(delegated):
        raise BindingError("invalid parameter partition")
    if not (set(fixed) | set(delegated)) <= set(properties) - {target.idempotency_parameter}:
        raise BindingError("unknown contract parameter")
    required = set(target.parameters.get("required", [])) - {target.idempotency_parameter}
    constants = {p for p, s in properties.items() if isinstance(s, dict)
                 and ("const" in s or len(s.get("enum", [])) == 1)}
    if required - set(fixed) - set(delegated) - constants:
        raise BindingError("unaccounted required parameter")
    bound = contract.model_copy(deep=True)
    relevant = set(fixed.values())
    for parameter, rule in bound.delegated_arguments.items():
        # A delegated destination cannot relabel a user-controlled value.
        if origins.get(rule.slot) == "user" or origins.get(parameter) == "user":
            raise BindingError("delegation overlaps user-fixed value")
        if rule.slot in fixed.values():
            raise BindingError("delegation overlaps fixed argument")
        if rule.source_call_index is not None:
            index = rule.source_call_index
            call_id = dispatched.get(index)
            if index >= len(proposal_calls) or call_id is None:
                raise BindingError("source did not dispatch")
        else:
            call_id = rule.source_call_id
        source = ledger.get(call_id)
        if (source is None or source.request_id != request_id or source.effect != "read"
                or source.status not in {"pending", "success"}):
            raise BindingError("invalid source call")
        relevant.update(source.dependencies)
        relevant.update(rule.match_slots.values())
        rule.source_call_index = None
        rule.source_call_id = call_id
    if any(name not in state.slots or not state.slots[name].confirmed
           or origins.get(name) != "user" for name in relevant):
        raise BindingError("constraint is not user-fixed")
    # Source dependencies must still denote these exact current values.
    for rule in bound.delegated_arguments.values():
        source = ledger[rule.source_call_id]
        if any(state.slots[n].revision != rev for n, rev in source.dependencies.items()):
            raise BindingError("source is stale")
    return BoundWrite(bound, request_id, input_epoch, state.intent,
                      {n: state.slots[n].revision for n in relevant})


def validate_binding(bound, proposed, *, state, ledger, results, invalidated,
                     manifest, request_id, input_epoch):
    """Return covered parameters, or reject the entire contracted write."""
    if (bound.request_id != request_id or bound.input_epoch != input_epoch
            or bound.intent != state.intent or bound.contract.tool != proposed.tool):
        raise BindingError("expired contract")
    if any(n not in state.slots or not state.slots[n].confirmed
           or state.slots[n].revision != rev for n, rev in bound.revisions.items()):
        raise BindingError("changed contract constraint")
    contract = bound.contract
    parameters = set(proposed.arguments) - {manifest.idempotency_parameter}
    if not (set(contract.fixed_arguments) | set(contract.delegated_arguments)) <= parameters:
        raise BindingError("missing contracted parameter")
    if set(proposed.result_sources) != set(contract.delegated_arguments):
        raise BindingError("missing or extra result source")
    for parameter in parameters:
        value = proposed.arguments[parameter]
        slot_name = proposed.argument_slots.get(parameter, parameter)
        if parameter in contract.fixed_arguments:
            expected_slot = contract.fixed_arguments[parameter]
            if slot_name != expected_slot or not json_equal(value, state.slots[expected_slot].value):
                raise BindingError("fixed argument mapping changed")
        elif parameter in contract.delegated_arguments:
            rule = contract.delegated_arguments[parameter]
            source = ledger.get(rule.source_call_id)
            if (proposed.result_sources[parameter] != rule.source_call_id
                    or slot_name != rule.slot or source is None or source.effect != "read"
                    or source.status != "success" or source.request_id != request_id
                    or source.call_id in invalidated):
                raise BindingError("invalid result provenance")
            if any(n not in state.slots or state.slots[n].revision != rev
                   for n, rev in source.dependencies.items()):
                raise BindingError("stale read")
            evidence = [r for r in results if r.call_id == source.call_id and r.status == "success"]
            if len(evidence) != 1 or evidence[0].error is not None:
                raise BindingError("source not in accepted results")
            selected = resolve_selection(evidence[0].result, rule.collection_pointer,
                                         rule.value_pointer,
                                         {p: state.slots[n].value for p, n in rule.match_slots.items()})
            slot = state.slots.get(rule.slot)
            if (slot is None or not json_equal(selected, value)
                    or not json_equal(selected, slot.value)):
                raise BindingError("selected value mismatch")
        else:
            schema = manifest.parameters.get("properties", {}).get(parameter, {})
            if not isinstance(schema, dict) or not ("const" in schema or len(schema.get("enum", [])) == 1):
                raise BindingError("unaccounted argument")
            fixed = schema["const"] if "const" in schema else schema["enum"][0]
            if parameter in proposed.argument_slots or not Draft202012Validator({"const": fixed}).is_valid(value):
                raise BindingError("invalid constant")
    return set(contract.delegated_arguments)
