"""One authoritative controller; workers return messages and never edit session state."""

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator, validate
from jsonschema.exceptions import ValidationError as PlanSchemaViolation

from .clock import RealClock
from .contracts import (
    AudioEvent, EndEvent, FrameEvent, InterruptEvent, Observation, OutputEvent,
    PlanProposal, ResultEvent, SessionView, Slot, Snapshot, StartEvent, ToolCall,
    ToolResult, TranscriptEvent,
)
from .corpus import (
    CORPUS_TOOL_NAME, CorpusAccessError, CorpusStore, best_passage, corpus_manifest, is_safe_query,
)


# Bound on any proposal-supplied value interpolated into a spoken/logged `clarify`
# text. PlanProposal.slot_updates is dict[str, Any] with no length limit, and under
# prompt injection its values (and proposal.intent) are attacker-controlled; this keeps
# the emitted text -- and the committed trace evidence it becomes part of -- bounded
# regardless of what the model proposes (security review LOW finding 2).
CLARIFY_VALUE_TRUNCATE_LEN = 200


def _clarify_repr(value):
    text = repr(value)
    if len(text) > CLARIFY_VALUE_TRUNCATE_LEN:
        return text[:CLARIFY_VALUE_TRUNCATE_LEN] + "...(truncated)"
    return text


# Slot/parameter NAMES interpolated into a clarify are just as planner-controlled and
# unbounded as the values _clarify_repr guards (PlanProposal.slot_updates keys,
# ProposedCall.arguments keys, and argument_slots values all come from the model's own
# proposal). The origin check that emits these clarifies runs before manifest
# validation, so a schema's additionalProperties:False cannot filter an oversized name
# in time (security review LOW finding 3).
def _clarify_name(name):
    text = str(name)
    if len(text) > CLARIFY_VALUE_TRUNCATE_LEN:
        return text[:CLARIFY_VALUE_TRUNCATE_LEN] + "...(truncated)"
    return text


class DenyWrites:
    def allows(self, view, call):
        return False


@dataclass
class WorkerMessage:
    kind: str
    generation: int
    value: object
    perception_epoch: int = 0
    source: tuple | None = None
    # True only for a "plan" message produced from a genuinely new observation
    # (new/partial speech or an image). False for a plan triggered internally by a
    # tool result, retry, or reconciliation continuation for the same request.
    fresh_evidence: bool = False


class Agent:
    ABLATIONS = frozenset({"dependency_invalidation"})

    def __init__(self, perception, turn_policy, reasoner, executor=None, authorization=None,
                 scenario_timeout=115, inference_timeout=25, partial_debounce_s=0.08,
                 frame_debounce_s=0.4, disabled=(), corpus_root=None):
        if scenario_timeout <= 0 or inference_timeout <= 0 or partial_debounce_s < 0:
            raise ValueError("Timeouts must be positive and debounce nonnegative")
        if frame_debounce_s < 0:
            raise ValueError("Timeouts must be positive and debounce nonnegative")
        unknown = set(disabled) - self.ABLATIONS
        if unknown:
            raise ValueError(f"Unknown ablation: {sorted(unknown)}")
        # Named components a baseline run may switch off. Every other behaviour, the model,
        # the tools and the scenarios stay identical so only this component is compared.
        self.disabled = frozenset(disabled)
        self.perception = perception
        self.turn_policy = turn_policy
        self.reasoner = reasoner
        self.executor = executor
        self.authorization = authorization or DenyWrites()
        self.scenario_timeout = min(scenario_timeout, 119)
        self.inference_timeout = inference_timeout
        self.partial_debounce_s = partial_debounce_s
        # A frame that arrives with nothing spoken yet waits this long before it answers
        # on its own. Someone who holds up a label and then asks about it produces a frame
        # and an utterance in quick succession; answering the frame instantly talks over
        # the question that was already coming. Speech inside the window cancels the
        # frame-only plan, so the two fold into one answer. When speech for this request
        # already exists the frame is answering it, so no wait applies and the
        # clarification path keeps its latency.
        self.frame_debounce_s = frame_debounce_s
        # Installed directory holding corpus documents. None means no corpus is wired up:
        # any session that still declares Start.corpus gets a bounded per-request refusal
        # (see _corpus_lookup) instead of a crash. A session with an empty corpus never
        # touches this at all -- see the StartEvent handling in run().
        #
        # Falls back to ACCESSFLOW_CORPUS_ROOT so the normal CLI/replay harness (which
        # constructs Agent without ever importing accessflow.corpus itself) has a way to
        # configure this trust boundary -- see cli.py's --corpus-root. An explicit
        # corpus_root=None argument is indistinguishable from "not given" here by design;
        # nothing in this codebase ever needs to force "no env fallback" while also
        # passing None explicitly.
        self._corpus_root = corpus_root if corpus_root is not None else os.getenv("ACCESSFLOW_CORPUS_ROOT")
        self.running = False

    async def run(self, input_queue, output_queue, clock=None):
        if self.running:
            raise RuntimeError("Use a separate Agent instance for each concurrent session")
        self.running = True
        self.clock = clock or RealClock()
        self.out = output_queue
        self.inbox = asyncio.Queue()
        self.workers = set()
        self.perception_workers = {}
        self.state = Snapshot()
        self.session_id = None
        self.manifests = {}
        self.observations = {}
        self.sources = {}
        self.results = []
        self.tool_failures = []
        # Monotonic count of admitted tool outcomes (results and failures), across the whole
        # session. Unlike len(self.results), never decreases: _invalidate_dependencies
        # removes stale entries FROM self.results (so a dependent slot update can drop
        # its own read's evidence), but must not be able to rewind this counter (H1).
        self._results_admitted = 0
        self.ledger = {}
        self.seen = set()
        self.dispatched = {}
        self.generation = 0
        self.request_id = str(uuid4())
        self.last_request_finished = False
        self.output_sequence = 0
        self.latest_complete = False
        self.planner = None
        # Metadata for whichever planner task self.planner currently refers to, so that
        # cancelling it (below, and in _start_plan) can tell whether the task it just
        # pre-empted was a fresh-evidence one that never got to deliver its proposal (H2).
        self._planner_fresh = False
        self._planner_key = None
        # (request_id, request_input_epoch) -> True when a fresh-evidence planner task
        # for that key was cancelled before it delivered a proposal. Consumed (popped) the
        # one time it is used to grant write authority to a subsequent non-fresh replan --
        # see the speech_origin block in _apply.
        self._fresh_plan_cancelled = {}
        self.repeated_completed_call = False
        self.no_progress = False
        self.repeat_recoveries = {}
        self.write_stall_recoveries = {}
        self.schema_rejection_recoveries = {}
        # Shared bounded-recovery budget for every no-progress mechanism above, keyed by
        # (request_id, request_input_epoch) so a request cannot chain several single-shot
        # mechanisms into unlimited retries, while a genuinely new utterance/frame for the
        # same still-open request still gets its own fresh attempt. The per-mechanism dicts
        # above are kept only for external introspection/back-compat; they no longer gate.
        self.recovery_budget = {}
        self.request_input_epoch = 0
        self.active_frame = None
        self.active_speech = None
        self.speech_ready = False
        # Retained spoken write authorization for the CURRENT request (self.request_id).
        # Set only from a completed ("ready") spoken utterance. Survives a clarifying
        # turn on the same request -- a clarifying question is unresolved information,
        # not a retraction of intent -- and is only granted or retracted by a genuinely
        # new spoken utterance's own write_requested flag. Never set or read from an
        # image proposal: an image may resolve missing information but cannot itself
        # authorize a write. Cleared on interrupt, explicit stop, and request
        # completion/rotation.
        self.write_intent_retained = False
        # Snapshot of self._results_admitted taken every time a fresh-evidence speech
        # proposal is processed (see _apply). A later non-fresh (tool-result-
        # triggered) replan may only newly grant write authority -- as opposed to
        # merely retaining authority a fresh proposal already gave it -- while this
        # mark still EQUALS self._results_admitted: i.e. no tool result has entered
        # evidence since the user's own utterance was last considered. self.results
        # itself is not usable for this: _invalidate_dependencies removes entries from
        # it (a slot update can invalidate its own read's result), so its length can
        # fall back to or below an earlier mark even though new evidence was admitted
        # in between -- that let a planner re-open write authority M4 was meant to
        # close (H1). _results_admitted only ever grows, so it cannot be rewound this
        # way. This mark alone is not sufficient to grant authority; _apply also
        # requires _fresh_plan_cancelled to record that a fresh-evidence plan for this
        # exact (request_id, request_input_epoch) was cancelled before delivering, so
        # only that pre-emption -- not an arbitrary non-fresh replan -- can hand off
        # authority a genuinely spoken request already earned (H2).
        self._write_authority_evidence_mark = 0
        # Slot names (and, via _intent_user_fixed, the intent) that a fresh-evidence
        # (user-origin) proposal has itself supplied a value for. Mirrors
        # write_intent_retained's provenance idea one level down: write AUTHORITY is
        # gated on fresh evidence, but until this, the ARGUMENTS of an already-
        # authorized write were not -- a tool-result-triggered replan could not create
        # permission to write, but could silently rewrite which value a permitted
        # write actually used (A17-1). A slot/intent name enters this set the first
        # time a fresh proposal sets it and is never removed (matching
        # slot_revisions' session-lifetime scope); a non-fresh proposal may still
        # freely SET a name that is not in this set at all -- that is a delegated
        # value ("book the first available day") the user never fixed, and a tool
        # result legitimately supplies it. See the speech_origin block in _apply.
        self._user_fixed_slots = set()
        self._intent_user_fixed = False
        # Origin of each slot's CURRENT value: "user" when a fresh-evidence, complete
        # (or completed-correction) proposal itself supplied that name in
        # slot_updates, "tool" when a non-fresh (tool-result-triggered) proposal did.
        # Distinct from _user_fixed_slots, which only locks a NAME against a non-fresh
        # CHANGE once the user has fixed it: that guard never fires for a slot the
        # user never named at all, and a tool-result replan is free to invent a brand
        # new slot (or alias a write's argument onto one via argument_slots) that no
        # name-keyed guard protects. This dict instead tracks, per slot, who last
        # supplied its value, so the write-dispatch path in _apply can require
        # explicit user confirmation before committing any write argument that
        # resolves (via ProposedCall.argument_slots) to a tool-supplied slot --
        # closing A17-1's parameter-alias variant regardless of what either the slot
        # or the parameter happens to be named (security review HIGH finding).
        # Session-scoped like slot_revisions would be wrong here: unlike
        # _user_fixed_slots (permanent once set), this must reset on the same
        # request-scoped boundaries as _user_fixed_slots below, so a delegated value
        # from a FINISHED request cannot block a write on an unrelated later one.
        self._slot_value_origin = {}
        # Whether the current request still has an unanswered clarifying question.
        # Blocks write dispatch independently of write_intent_retained so a resolved
        # or still-open information gap is never conflated with the user's underlying
        # authorization to write.
        self.clarification_outstanding = False
        self.semantic_correction_event = None
        self.last_sequence = -1
        self.invalidated = set()
        self.perception_epoch = 0
        self.source_events = {}
        self.provisional_slots = {}
        self.slot_revisions = {}
        self.provisional_intent = None
        self.attempt_counts = {}
        self.planning_source = None
        self.current_event_id = None
        self.call_causes = {}
        self._fresh_evidence = False
        # Session-scoped corpus state. Reinitialized fresh here on every run() (a session
        # boundary already shared by every other piece of state above) so corpus access
        # from a previous session can never leak into a new one. Populated only if the
        # StartEvent declares a non-empty corpus; an empty corpus leaves these at their
        # defaults and self.manifests never gains the corpus tool -- see StartEvent below.
        self.corpus_root = Path(self._corpus_root) if self._corpus_root else None
        self.corpus_allowlist = frozenset()
        self.corpus_store = None
        # True only once THIS session's StartEvent actually installed the built-in
        # corpus capability (a non-empty Start.corpus). Dispatch and cancellation route
        # to the internal implementation on this flag, never merely on a call's tool
        # name -- see _execute/_cancel. Fixes M3: an empty corpus plus an external
        # manifest that happens to be named "search_corpus" must reach that external
        # executor unchanged, not be silently intercepted here.
        self._corpus_installed = False

        async def pump():
            while True:
                await self.inbox.put(await input_queue.get())

        async def deadline():
            await self.clock.sleep(self.scenario_timeout)
            await self.inbox.put(WorkerMessage("deadline", 0, None))

        self._spawn(pump())
        self._spawn(deadline())
        try:
            while True:
                event = await self.inbox.get()
                if isinstance(event, WorkerMessage):
                    if event.kind == "deadline":
                        await self._shutdown("scenario_timeout")
                        break
                    await self._worker(event)
                    continue
                if isinstance(event, StartEvent):
                    if self.session_id is not None:
                        await self._emit("error", code="session_already_started")
                        continue
                    names = [tool.name for tool in event.payload.tools]
                    if len(names) != len(set(names)):
                        self.session_id = event.session_id
                        await self._emit("error", code="duplicate_manifest_names")
                        break
                    self.session_id = event.session_id
                    self.manifests = {tool.name: tool.model_copy(deep=True) for tool in event.payload.tools}
                    if any(tool.status_tool and (tool.status_tool not in self.manifests or
                           self.manifests[tool.status_tool].effect != "read") for tool in self.manifests.values()):
                        await self._emit("error", code="invalid_status_tool_manifest")
                        break
                    # Corpus document names are already validated (safe, unique) by
                    # Start.valid_corpus; only the cross-item manifest-name collision is
                    # this controller's own concern, same as duplicate_manifest_names above.
                    if event.payload.corpus:
                        if CORPUS_TOOL_NAME in self.manifests:
                            await self._emit("error", code="duplicate_manifest_names")
                            break
                        self.manifests[CORPUS_TOOL_NAME] = corpus_manifest(event.payload.corpus)
                        self.corpus_allowlist = frozenset(event.payload.corpus)
                        self.corpus_store = CorpusStore(self.corpus_root) if self.corpus_root else None
                        self._corpus_installed = True
                    self.seen.add(event.event_id)
                    self.last_sequence = event.sequence
                    continue
                if self.session_id is None:
                    # No outgoing event may impersonate an as-yet unstarted session.
                    continue
                if event.session_id != self.session_id:
                    await self._emit("error", code="wrong_session")
                    continue
                if event.event_id in self.seen:
                    continue
                self.seen.add(event.event_id)
                self.current_event_id = event.event_id
                if isinstance(event, EndEvent):
                    await self._shutdown(event.payload.reason)
                    break
                if isinstance(event, ResultEvent):
                    await self._result(event.payload)
                    continue
                # Sequence is advisory across producers; source revisions gate hypotheses.
                self.last_sequence = max(self.last_sequence, event.sequence)
                if isinstance(event, InterruptEvent):
                    self.generation += 1
                    self.perception_epoch += 1
                    for worker in tuple(self.perception_workers.values()):
                        worker.cancel()
                    if self.planner and not self.planner.done():
                        self.planner.cancel()
                    self.latest_complete = False
                    self.speech_ready = False
                    self.write_intent_retained = False
                    self.clarification_outstanding = False
                    # Request-scoped authority, same lifetime as the two flags above (see
                    # the identical reset on request rotation below) -- an interrupt must
                    # not leave a slot/intent the user fixed before the interrupt able to
                    # permanently outlive it (security review MEDIUM finding 1).
                    self._user_fixed_slots = set()
                    self._intent_user_fixed = False
                    # _slot_value_origin is NOT the same kind of state as the two flags
                    # above. A "user" mark is request-scoped authority (the user fixed
                    # THIS slot on THIS request) and must keep being wiped here. A
                    # "tool"/"image" mark is taint ON A VALUE, and that value is not
                    # request-scoped -- self.state.slots is untouched by an interrupt, so
                    # the tainted value survives it. Wiping the whole dict unconditionally
                    # discarded the mark while the value it described lived on: the very
                    # next dispatch check then saw origin=None (not "tool") for that slot
                    # and let the interrupted turn's planner-injected value commit
                    # (security review HIGH finding 1). Keep every non-"user" mark whose
                    # slot still exists; only "user" marks reset here.
                    self._slot_value_origin = {name: origin for name, origin in self._slot_value_origin.items()
                                               if origin != "user" and name in self.state.slots}
                    self.semantic_correction_event = None
                    self.state.correction_pending = True
                    await self._cancel_writes("interrupted")
                    if event.payload.scope == "task":
                        for call in list(self.ledger.values()):
                            if call.status == "pending":
                                await self._cancel(call, "task_stopped")
                        self.state.status = "stopped"
                    await self._emit("acknowledge", text="Stopped." if event.payload.scope == "task"
                                     else "I'm listening.", stop_output=True)
                    continue
                if isinstance(event, (TranscriptEvent, AudioEvent, FrameEvent)):
                    payload = event.payload
                    if isinstance(event, FrameEvent):
                        source = ("image", payload.frame_id)
                        revision = 0
                    else:
                        source = ("speech", payload.utterance_id)
                        revision = payload.revision
                    if revision <= self.sources.get(source, -1):
                        continue
                    if source[0] == "image" and self.active_frame is not None:
                        previous_source = ("image", self.active_frame)
                        previous_worker = self.perception_workers.get(previous_source)
                        if previous_worker:
                            previous_worker.cancel()
                        await self._rollback_hypothesis(previous_source)
                        self.observations.pop(previous_source, None)
                    await self._rollback_hypothesis(source)
                    self.sources[source] = revision
                    self.source_events[source] = event.event_id
                    if source[0] == "image":
                        self.active_frame = source[1]
                    if source[0] == "speech":
                        self.active_speech = source[1]
                        self.speech_ready = False
                        self.write_intent_retained = False
                        self.semantic_correction_event = None
                    if self.last_request_finished:
                        self.request_id = str(uuid4())
                        self.last_request_finished = False
                        self.write_intent_retained = False
                        self.clarification_outstanding = False
                        # A new request must not inherit authority over slots/intent the
                        # user fixed on a now-finished prior request -- otherwise a
                        # legitimate delegated value on THIS request (the user names no
                        # day; a later tool result honestly supplies one) is permanently
                        # refused by a lock left over from an unrelated earlier request
                        # (security review MEDIUM finding 1). self.state.slots itself is
                        # untouched here; only the fixed-by-user PROVENANCE resets.
                        self._user_fixed_slots = set()
                        self._intent_user_fixed = False
                        # Same reasoning as the identical reset on InterruptEvent above:
                        # only "user" marks are request-scoped authority. A "tool"/"image"
                        # mark describes the surviving VALUE (self.state.slots is not
                        # touched by a rotation either), so wiping it here while the value
                        # lives on let a rotation-triggered replan launder a tool-origin
                        # value straight past the dispatch check on the new request
                        # (security review HIGH finding 1).
                        self._slot_value_origin = {name: origin for name, origin in self._slot_value_origin.items()
                                                   if origin != "user" and name in self.state.slots}
                    self.generation += 1
                    self.latest_complete = False
                    self.state.correction_pending = True
                    self.state.status = "listening"
                    # Conservative write guard until semantic/dependency resolution.
                    await self._cancel_writes("new_evidence")
                    self._start_perception(event, source)
        finally:
            pending = list(self.workers)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            self.running = False

    def _spawn(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.workers.add(task)
        task.add_done_callback(self.workers.discard)
        return task

    def _start_perception(self, event, source):
        previous = self.perception_workers.get(source)
        if previous:
            previous.cancel()
        task = self._spawn(self._perceive(event.model_copy(deep=True), self.generation, self.perception_epoch))
        self.perception_workers[source] = task

        def retire(done):
            if self.perception_workers.get(source) is done:
                self.perception_workers.pop(source)

        task.add_done_callback(retire)

    async def _bounded(self, awaitable, seconds):
        work = asyncio.create_task(awaitable)
        timer = asyncio.create_task(self.clock.sleep(seconds))
        try:
            done, _ = await asyncio.wait({work, timer}, return_when=asyncio.FIRST_COMPLETED)
            if work in done:
                return work.result()
            raise TimeoutError("Worker deadline exceeded")
        finally:
            work.cancel()
            timer.cancel()
            await asyncio.gather(work, timer, return_exceptions=True)

    async def _perceive(self, event, generation, epoch):
        async def collect():
            async for observation in self.perception.observe(event):
                await self.inbox.put(WorkerMessage("observation", generation, observation.model_copy(deep=True), epoch))
        try:
            await self._bounded(collect(), self.inference_timeout)
        except Exception as exc:
            await self.inbox.put(WorkerMessage("failure", generation, type(exc).__name__))

    def _view(self):
        self.state.pending_call_ids = [c.call_id for c in self.ledger.values() if c.status == "pending"]
        return SessionView(session_id=self.session_id, state=self.state.model_copy(deep=True),
                           observations=[o.model_copy(deep=True) for o in list(self.observations.values())[-24:]],
                           results=[r.model_copy(deep=True) for r in self.results[-12:]],
                           tool_failures=[r.model_copy(deep=True) for r in self.tool_failures
                               if self.ledger[r.call_id].request_id == self.request_id
                               and all(self.state.slots.get(key) and self.state.slots[key].revision == revision
                                   for key, revision in self.ledger[r.call_id].dependencies.items())],
                           calls=[c.model_copy(deep=True) for c in self.ledger.values()],
                           write_pending=self.write_intent_retained,
                           repeated_completed_call=self.repeated_completed_call,
                           no_progress=self.no_progress,
                           active_request_id=self.request_id)

    async def _emit(self, kind, **payload):
        if self.current_event_id is not None:
            payload.setdefault("caused_by_event_id", self.current_event_id)
        self.output_sequence += 1
        view = self._view()
        await self.out.put(OutputEvent(session_id=self.session_id, sequence=self.output_sequence,
                                      timestamp=self.clock.now(), kind=kind, payload=payload, state=view.state))

    async def _worker(self, message):
        if message.kind == "tool":
            await self._result(message.value)
            return
        if message.kind != "observation" and message.generation != self.generation:
            return
        if message.kind == "failure":
            await self._emit("error", code="backend_failure", detail=message.value)
        elif message.kind == "observation":
            if message.perception_epoch != self.perception_epoch:
                return
            obs: Observation = message.value
            key = ("image" if obs.modality == "image" else "speech", obs.source_id)
            if self.sources.get(key) != obs.revision or self.source_events.get(key) != obs.event_id:
                return
            if obs.modality == "image" and obs.source_id != self.active_frame:
                return
            if obs.modality != "image" and obs.source_id != self.active_speech:
                return
            self.current_event_id = obs.event_id
            self.observations[key] = obs
            decision = self.turn_policy.update(obs.model_copy(deep=True), self._view())
            if obs.modality != "image" and obs.source_id == self.active_speech:
                self.speech_ready = decision.kind == "complete" and obs.final
                self.semantic_correction_event = obs.event_id if (
                    obs.final and decision.kind == "possible_correction") else None
            self.latest_complete = self.speech_ready
            if obs.modality == "image":
                # An image can invite an informational answer on its own. It does
                # not finish pending speech or authorize a state-changing action.
                #
                # Readiness comes from the observation, not from the turn policy. The
                # policy answers one question -- has the speaker finished this utterance
                # -- and a frame is not an utterance, so it has no turn to end. Asking
                # the policy about a frame also drags the caption text through the
                # backchannel and correction rules, where "okay" in a photo reads as a
                # backchannel. HeuristicTurnPolicy now returns "continue" for every
                # image for that reason, so a policy verdict here would stall every
                # frame permanently.
                self.latest_complete = (self.speech_ready or self.active_speech is None) and obs.final
            self.state.correction_pending = not self.latest_complete
            if decision.kind == "stop":
                self.generation += 1
                self.perception_epoch += 1
                self.write_intent_retained = False
                self.clarification_outstanding = False
                await self._cancel_writes("explicit_stop")
                self.state.status = "stopped"
                await self._emit("acknowledge", text="Stopped.", stop_output=True)
                return
            if decision.kind == "backchannel":
                return
            if obs.modality != "image" and (self.latest_complete
                                            or (obs.final and decision.kind == "possible_correction")):
                # A final correction can be acknowledged while semantics are still
                # unresolved. This does not mark the request complete or authorize
                # a write; partial speech continues without an interjection.
                #
                # Speech only. "I'll check that." answers a speaker who is waiting to
                # hear that the turn landed. A frame has no speaker waiting on it, so
                # the same interjection is noise in the output stream.
                await self._emit("acknowledge", text="I'll check that.", backend=obs.backend)
            # Partial plans may prepare reads but may never authorize writes.
            self._start_plan(source=key)
        elif message.kind == "plan":
            self.current_event_id = self.source_events.get(message.source)
            # Stashed on self (rather than an _apply parameter) so subclasses that
            # override _apply(self, plan, source=None) -- its signature before this
            # fix -- keep working unchanged.
            self._fresh_evidence = message.fresh_evidence
            await self._apply(message.value, message.source)
        elif message.kind == "plan_rejected":
            await self._emit("error", code="plan_schema_rejected", detail=message.value)
            await self._offer_recovery(self.schema_rejection_recoveries)

    def _start_plan(self, source=None):
        self.generation += 1
        # A source given here comes from _worker's observation handling and means new
        # user evidence (fresh/partial speech, or an image) just arrived. Every other
        # caller reuses the existing planning_source to continue reasoning about the
        # same request (a tool result, a bounded retry, a reconciliation step) and
        # must not be mistaken for new evidence about user intent.
        fresh_evidence = source is not None
        if source is not None:
            self.planning_source = source
            # Genuinely new evidence about this still-open request earns its own
            # bounded recovery budget instead of inheriting an exhausted one from
            # an earlier, unrelated stall on the same request_id.
            self.request_input_epoch += 1
            # request_input_epoch only ever grows (never resets, even across
            # request_id rotation -- see run()), and _apply only ever pops a
            # _fresh_plan_cancelled entry keyed to the CURRENT epoch. So the instant
            # epoch advances past an entry's own epoch, that entry can never again be
            # popped: it is dead the moment this bump makes it stale, not merely old.
            # Drop it now instead of keeping a live-forever, never-consumable record
            # for the rest of the session (security review LOW 1).
            if self._fresh_plan_cancelled:
                self._fresh_plan_cancelled = {key: v for key, v in self._fresh_plan_cancelled.items()
                                              if key[1] >= self.request_input_epoch}
        source = self.planning_source
        if self.planner and not self.planner.done():
            self.planner.cancel()
            # self._planner_key[1] can only be < self.request_input_epoch here when
            # THIS call just bumped the epoch above (a new-evidence pre-emption of an
            # in-flight fresh plan): that key is already stale by the pruning rule
            # above and recording it would just recreate what was pruned two lines
            # up. It equals the current epoch when this call did not bump it (a
            # same-epoch, non-fresh pre-emption, e.g. an internal retry) -- the one
            # case that is still legitimately consumable below.
            if self._planner_fresh and self._planner_key[1] == self.request_input_epoch:
                # The task being pre-empted here was reasoning on fresh user evidence
                # and never got to deliver a proposal. Record that for its
                # (request_id, request_input_epoch) so a legitimate hand-off to this
                # replacement plan can retain (not create) the authority that
                # evidence would have granted -- see the speech_origin block in
                # _apply (H2). Consumed there the one time it is used.
                self._fresh_plan_cancelled[self._planner_key] = True
        view = self._view()
        generation = self.generation
        lone_frame = source is not None and source[0] == "image" and self.active_speech is None
        self._planner_fresh = fresh_evidence
        self._planner_key = (self.request_id, self.request_input_epoch)

        async def plan():
            try:
                if lone_frame and self.frame_debounce_s:
                    await self.clock.sleep(self.frame_debounce_s)
                elif view.state.correction_pending and self.partial_debounce_s:
                    await self.clock.sleep(self.partial_debounce_s)
                proposal = await self._bounded(self.reasoner.plan(view, [m.model_copy(deep=True)
                                                                        for m in self.manifests.values()]),
                                               self.inference_timeout)
                await self.inbox.put(WorkerMessage("plan", generation, proposal.model_copy(deep=True),
                                                   source=source, fresh_evidence=fresh_evidence))
            except PlanSchemaViolation as exc:
                # The reasoner's own generation failed the exact schema built for this
                # request (dynamic tool/effect restrictions, forced null response, ...).
                # This is a rejection, not a generic backend outage: route it into a
                # bounded correction attempt instead of a silent stall.
                await self.inbox.put(WorkerMessage("plan_rejected", generation, str(exc)))
            except Exception as exc:
                await self.inbox.put(WorkerMessage("failure", generation, type(exc).__name__))
        self.planner = self._spawn(plan())

    async def _offer_recovery(self, compat_bucket):
        """Grant one bounded re-plan for the active (request, input revision), or fail explicitly.

        Every no-progress mechanism -- schema rejection, a stalled owed write, a repeated or
        otherwise undispatchable call, an empty plan -- draws from this single shared budget
        instead of each getting its own independent attempt, so a request cannot chain several
        single-shot mechanisms into unbounded retries. `compat_bucket`, when given, is one of
        the pre-existing per-mechanism dicts (repeat_recoveries, write_stall_recoveries,
        schema_rejection_recoveries); it is still incremented for external introspection and
        the tests that key off it, but it no longer independently gates the retry.
        On exhaustion this ends the request with an explicit diagnostic instead of leaving it
        to silently wait for the scenario deadline.
        """
        if self.state.status in {"stopped", "ended"}:
            return
        key = (self.request_id, self.request_input_epoch)
        used = self.recovery_budget.get(key, 0)
        if used < 1:
            self.recovery_budget[key] = used + 1
            if compat_bucket is not None:
                compat_bucket[self.request_id] = compat_bucket.get(self.request_id, 0) + 1
            self._start_plan()
            return
        if not self.last_request_finished:
            self.last_request_finished = True
            self.state.status = "no_progress"
            await self._emit("error", code="no_progress_exhausted",
                             message="No progress after one bounded automatic retry; this "
                                     "request will not retry again on its own.")

    async def _apply(self, proposal: PlanProposal, source=None):
        fresh_evidence = self._fresh_evidence
        # Snapshot before this proposal can mutate write_intent_retained below. Mirrors
        # ModelReasoner.write_outstanding: true when the CURRENT request's spoken write
        # request names a real write tool that has not been dispatched or confirmed by
        # any call the current request has made yet. Scoped to self.request_id so an
        # old, unrelated write earlier in the session cannot silently satisfy (or
        # continuation-block) a brand new request -- see ToolCall.request_id.
        prior_write_owed = (self.write_intent_retained
                            and any(m.effect == "write" for m in self.manifests.values())
                            and not any(call.effect == "write" and call.status in {"pending", "success", "unknown"}
                                       for call in self.ledger.values()
                                       if call.request_id == self.request_id))
        self.repeated_completed_call = False
        self.no_progress = False
        repeated, dispatched_any, blocked_calls = [], False, 0
        speech = self.observations.get(("speech", self.active_speech))
        speech_origin = source == ("speech", self.active_speech)
        final_correction = bool(speech_origin and speech and speech.final and
                                speech.event_id == self.semantic_correction_event)
        if final_correction and proposal.request_complete and not proposal.clarification:
            # The policy flagged a completed utterance as a possible correction.
            # A fresh semantic plan can resolve it; a partial hypothesis cannot
            # become complete merely because the model requests a write.
            self.speech_ready = True
            self.latest_complete = True
            self.state.correction_pending = False
            self.semantic_correction_event = None
        if speech_origin:
            # Write authority is user-origin authority: only a proposal made on
            # fresh user speech evidence (fresh_evidence=True) may ESTABLISH or
            # RETRACT it, in either direction, matching prior behaviour -- it can
            # newly recognise intent or retract it (an explicit correction/
            # cancellation is new user evidence).
            #
            # A clarifying question is unresolved information, not a retraction: a
            # completed utterance that both requests a write AND asks a clarification
            # (e.g. "book the date shown in this image") must keep that intent alive
            # for a later turn on the SAME request to complete it once the missing
            # information (spoken or visual) arrives. Only the write_requested flag
            # itself -- never the presence of a clarification -- grants or retracts
            # intent here.
            #
            # A plan triggered by a tool result for this same request
            # (fresh_evidence=False) is an evidence-derived planning decision, not
            # user evidence. It may RETAIN authority the user's own utterance already
            # established, and a legitimate "read the support notes, then book if
            # appropriate" request still works because its authority comes from the
            # first speech-origin proposal -- the one that saw the user's own
            # utterance -- carrying write_requested=True from the start. What a
            # tool-result replan must never do is CREATE authority from evidence no
            # user utterance gave: retrieved document text or any other NEW tool
            # result must not be able to set write_intent_retained here just because
            # it prompted this replan.
            #
            # "New tool result" is enforced two ways, both required. First,
            # _results_admitted -- a counter incremented on every append to
            # self.results and NEVER decremented -- must still equal the mark taken
            # when fresh evidence was last considered: self.results itself is not
            # monotonic (_invalidate_dependencies drops entries from it when a slot
            # update invalidates their read), so a planner that updates a slot its own
            # read declared as a dependency could otherwise wind the mark back and
            # smuggle a later replan past this guard (H1). Second, this exact
            # (request_id, request_input_epoch) must be recorded in
            # _fresh_plan_cancelled: the only legitimate non-fresh grant is a fresh
            # plan that got pre-empted and cancelled before delivering (e.g. by an
            # unrelated internal retry, such as a stale write's own cancellation
            # confirmation) and handed off to this replacement, which then sees no
            # evidence the pending fresh plan would not also have seen. An ordinary
            # non-fresh replan -- e.g. one produced by _offer_recovery after
            # no_progress -- is not such a hand-off and must not qualify merely for
            # being non-fresh (H2). The flag is popped (consumed) so a single
            # cancelled fresh plan cannot authorize more than one later replan.
            if fresh_evidence:
                self.write_intent_retained = bool(self.speech_ready and proposal.write_requested)
                self._write_authority_evidence_mark = self._results_admitted
            elif (proposal.write_requested and self.speech_ready and not proposal.clarification
                    and self._results_admitted == self._write_authority_evidence_mark
                    and self._fresh_plan_cancelled.pop((self.request_id, self.request_input_epoch), False)):
                self.write_intent_retained = True
                # This proposal IS the fresh evidence, merely delivered by a
                # replacement (non-fresh-labelled) planner task rather than the
                # cancelled original -- see the H2 comment above. Its slot/intent
                # updates get the same provenance as a directly fresh proposal's
                # would, or a legitimate correction delivered exactly this way (e.g.
                # a write cancellation racing the next utterance) would be refused by
                # the guard below as if it were an unrelated tool result.
                fresh_evidence = True
        # Origin classification (security review HIGH finding 2): fresh_evidence alone
        # conflates "the user just said this" with "a camera frame just showed this" --
        # both an image and fresh speech set fresh_evidence=True. user_origin is the
        # strictly narrower predicate the three slot/intent provenance sites below
        # actually need: fresh AND speech-sourced. An image proposal has
        # fresh_evidence=True but speech_origin=False, so user_origin is False for it --
        # it can still SET a slot (as "image" origin, in the loop below) but can never
        # overwrite a slot the user already fixed by speech, and can never itself mark a
        # slot/intent "user"-fixed. The H2 hand-off above only ever sets
        # fresh_evidence=True inside `if speech_origin:`, so by the time it fires
        # speech_origin is already True and user_origin correctly follows fresh_evidence.
        user_origin = fresh_evidence and speech_origin
        changed = set()
        for name, value in proposal.slot_updates.items():
            old = self.state.slots.get(name)
            if not user_origin and name in self._user_fixed_slots and old is not None and old.value != value:
                # A17-1: write AUTHORITY (write_intent_retained, above) is gated on
                # fresh evidence; the ARGUMENTS of an already-authorized write must be
                # too. A tool-result-triggered replan cannot rewrite a slot value the
                # user themselves already fixed with their own speech -- it can still
                # freely SET a slot the user never fixed (see the comment on
                # self._user_fixed_slots in run()). Refusing here, rather than
                # silently applying it, is what stops a dispatched call from later
                # using the smuggled value: _argument_dependency_error grounds every
                # call argument against the CURRENT tracked slot value, so keeping the
                # old value here also keeps any pending write's arguments honest.
                #
                # Gated on user_origin, not merely fresh_evidence (security review HIGH
                # finding 2): fresh_evidence is also True for an image proposal, which
                # is not a user assertion and must be refused here exactly like a
                # tool-result replan -- otherwise a camera frame could overwrite a slot
                # the user fixed by speech and then get relabelled "user" below.
                if self.latest_complete or final_correction:
                    # Gated exactly like the proposal.clarification emit below: a
                    # mid-partial-utterance refusal would interrupt the speaker over
                    # something that has not finished being said (security review LOW
                    # finding 2). The refusal itself (the `continue` below, which keeps
                    # the original value) is NOT gated -- it must hold every time,
                    # partial or complete, matching the A17-1 guard this speaks for.
                    await self._emit("clarify", text=(
                        f"A tool result tried to change '{_clarify_name(name)}' from "
                        f"{_clarify_repr(old.value)} to {_clarify_repr(value)} after the "
                        "user already fixed it; the original value is kept."))
                continue
            value_changed = old is None or old.value != value
            if user_origin and self.latest_complete:
                # Gated on latest_complete: a still-partial hypothesis's slot value can
                # be discarded wholesale by _rollback_hypothesis, but until this gate,
                # merely PROPOSING it on fresh (user-origin) evidence already marked the
                # name permanently fixed here -- even after its value was rolled back,
                # even for the rest of the session (security review MEDIUM finding 1).
                # Only a proposal the turn policy considers COMPLETE (or a completed
                # correction) genuinely fixes a slot's provenance.
                self._user_fixed_slots.add(name)
                # A fresh, complete, SPEECH-origin proposal asserting this name is the
                # user's own confirmation of its value -- record that even when the
                # value is unchanged (e.g. the user explicitly confirming a value a
                # tool already delegated: see the write-dispatch origin check below).
                # This is the one case that touches origin without a value change, and
                # it is deliberately NOT symmetric with the "image"/"tool" cases below:
                # only a fresh, complete, speech-origin assertion can promote a slot to
                # "user" (security review HIGH finding 2).
                self._slot_value_origin[name] = "user"
            elif fresh_evidence and not speech_origin and value_changed:
                # Fresh, non-speech evidence (a frame) changed this slot's value. It is
                # weaker than a user assertion -- it never fixes the slot name (the
                # guard above still refuses it against an already user-fixed slot) and
                # never marks itself "user" -- but it is not planner-invented the way a
                # tool result is either, so it may dispatch a write unconfirmed (see the
                # write-dispatch origin check further down). The one exception: a slot
                # already tainted "tool" must not be laundered back to a dispatchable
                # origin just because a later image turn re-asserts the same
                # planner-supplied value, so a "tool" mark is never downgraded here
                # (security review HIGH finding 2).
                if self._slot_value_origin.get(name) != "tool":
                    self._slot_value_origin[name] = "image"
            elif not fresh_evidence and value_changed:
                # A non-fresh (tool-result-triggered) proposal is about to WRITE a new
                # value for `name` below (see `value_changed`, which this mirrors).
                # That value's provenance is not "the user just fixed this" nor "a
                # frame just showed this", so a write dispatch grounding on it must not
                # treat it as confirmed (see the write-dispatch origin check further
                # down in _apply). A non-fresh proposal merely REPEATING an unchanged
                # value, or a still-partial fresh one, leaves an already-recorded
                # origin alone -- e.g. a bounded retry replan that resends the same
                # fresh-set slot verbatim after a failed write must not downgrade it to
                # "tool".
                self._slot_value_origin[name] = "tool"
            if not self.latest_complete and name not in self.provisional_slots:
                self.provisional_slots[name] = (source,
                                                old.model_copy(deep=True) if old else None)
            elif not self.latest_complete and self.provisional_slots[name][0] != source:
                self.provisional_slots[name] = (source, self.provisional_slots[name][1])
            elif self.latest_complete:
                self.provisional_slots.pop(name, None)
            if value_changed:
                changed.add(name)
                self.slot_revisions[name] = self.slot_revisions.get(name, 0) + 1
                self.state.slots[name] = Slot(value=value, confirmed=self.latest_complete,
                                              revision=self.slot_revisions[name],
                                              evidence=[o.event_id for o in self.observations.values()])
            elif self.latest_complete:
                old.confirmed = True
        intent_conflict = (proposal.intent is not None and not fresh_evidence and self._intent_user_fixed
                           and proposal.intent != self.state.intent)
        if changed or (proposal.intent is not None and not intent_conflict
                       and proposal.intent != self.state.intent):
            self.state.revision += 1
        if intent_conflict:
            # Same provenance rule as slots, applied to the intent itself. The refusal
            # (self.state.intent is simply never reassigned when intent_conflict is
            # True) is unconditional; only the spoken/logged announcement is gated,
            # same as the slot-refusal clarify above (security review LOW finding 2).
            if self.latest_complete or final_correction:
                await self._emit("clarify", text=(
                    f"A tool result tried to change the intent from {_clarify_repr(self.state.intent)} to "
                    f"{_clarify_repr(proposal.intent)} after the user already fixed it; the original "
                    "intent is kept."))
        elif proposal.intent is not None:
            if not self.latest_complete and self.provisional_intent is None:
                self.provisional_intent = (source, self.state.intent)
            elif self.latest_complete:
                self.provisional_intent = None
            self.state.intent = proposal.intent
            if user_origin:
                # Gated on user_origin, not merely fresh_evidence, for the same reason
                # as the slot-provenance sites above: an image proposal must not be able
                # to mark the intent "user"-fixed on the strength of a camera frame
                # (security review HIGH finding 2).
                self._intent_user_fixed = True
        await self._invalidate_dependencies(changed, "dependency_changed")
        said_something = bool(proposal.clarification)
        if proposal.clarification and (self.latest_complete or final_correction):
            # Required information is now outstanding for this request. This is tracked
            # separately from write_intent_retained: asking a question never touches
            # whether the user authorized a write, only whether dispatch may proceed yet.
            self.clarification_outstanding = True
            self.state.status = "clarifying"
            await self._emit("clarify", text=proposal.clarification)
        elif self.latest_complete or final_correction:
            # A complete turn that does not clarify is the model's own signal that any
            # previously missing information (spoken or supplied by an image) is now
            # resolved for this request.
            self.clarification_outstanding = False
        for proposed in proposal.calls:
            manifest = self.manifests.get(proposed.tool)
            if not manifest:
                await self._emit("error", code="unknown_tool", tool=proposed.tool)
                blocked_calls += 1
                continue
            dependency_error = self._argument_dependency_error(proposed, manifest)
            if dependency_error:
                await self._emit("error", code=dependency_error, tool=proposed.tool)
                blocked_calls += 1
                continue
            if manifest.effect == "write":
                if not (self.latest_complete and self.speech_ready and self.write_intent_retained
                        and proposal.request_complete and proposal.write_requested
                        and not self.state.correction_pending and not proposal.clarification
                        and not self.clarification_outstanding):
                    blocked_calls += 1
                    continue
                if any(not self.state.slots[name].confirmed for name in proposed.dependencies):
                    blocked_calls += 1
                    continue
                # A17-1 (confirm-on-tool-origin): a name-keyed guard cannot stop a
                # tool-result replan from smuggling a value into an already-authorized
                # write, because the attack and a legitimate delegated value ("book the
                # first available day", where a tool result honestly supplies the day)
                # are structurally identical -- in both, a non-fresh replan sets a slot
                # the user never fixed and grounds the write on it. The controller
                # cannot see the user's utterance, only the planner-chosen slot name,
                # and that name need not match the write's own parameter name (a
                # planner can invent a brand-new slot, or alias the parameter onto one
                # via argument_slots, and no NAME the guard above keys on is ever
                # rewritten). So instead of trusting names, require the value's own
                # provenance: resolve each argument's EFFECTIVE slot exactly as
                # _argument_dependency_error does (argument_slots takes priority over
                # the parameter's own name) and refuse to commit if that slot's current
                # value was last supplied by a non-fresh (tool-result-triggered)
                # proposal rather than the user. This still lets a tool legitimately
                # supply a delegated value -- it just cannot make that value commit
                # unconfirmed; a later fresh utterance that sets the same slot flips
                # its origin to "user" and unblocks the write on a subsequent turn.
                tool_origin_arg = next(
                    (parameter for parameter in proposed.arguments
                     if parameter != manifest.idempotency_parameter
                     and self._slot_value_origin.get(
                         proposed.argument_slots.get(parameter, parameter)) == "tool"),
                    None)
                if tool_origin_arg is not None:
                    slot_name = proposed.argument_slots.get(tool_origin_arg, tool_origin_arg)
                    value = proposed.arguments[tool_origin_arg]
                    if self.latest_complete or final_correction:
                        # Gated exactly like the neighbouring provenance-refusal emits
                        # above (security review LOW finding 2): only announced once the
                        # utterance is actually complete, never mid-partial-speech. The
                        # refusal itself (the `continue` below) is unconditional.
                        await self._emit("clarify", text=(
                            f"'{proposed.tool}' would commit with {_clarify_name(tool_origin_arg)}="
                            f"{_clarify_repr(value)}, grounded on '{_clarify_name(slot_name)}' whose "
                            "value a tool result supplied rather than the user; please confirm "
                            "this before it can be committed."))
                    self.clarification_outstanding = True
                    said_something = True
                    continue
                # Unknown/cancelled writes may have committed: no new write until reconciled.
                if any(c.effect == "write" and c.status in {"unknown", "cancelled"} for c in self.ledger.values()):
                    await self._emit("clarify", text="The earlier action has an unresolved outcome; check its status first.")
                    said_something = True
                    continue
            # A dependency name may be ledger operation identity rather than a slot
            # (see _argument_dependency_error); those carry no slot revision to track.
            dependencies = {name: self.state.slots[name].revision for name in proposed.dependencies
                            if name in self.state.slots}
            args = dict(proposed.arguments)
            # This field belongs to the controller, including when a model supplies
            # a different value on each retry. It cannot split a logical operation.
            if manifest.idempotency_parameter:
                args.pop(manifest.idempotency_parameter, None)
            signature = json.dumps([self.request_id, proposed.tool, args, dependencies], sort_keys=True)
            previous = self.ledger.get(self.dispatched.get(signature))
            if previous and (previous.status != "failed" or self.attempt_counts[signature] >= 2):
                if previous.status == "success":
                    repeated.append(previous.call_id)
                elif previous.status == "failed":
                    # A permanently failed call (its one bounded retry already used) proposed
                    # again verbatim is not new work either; it just never got flagged before.
                    blocked_calls += 1
                continue
            operation_id = previous.operation_id if previous else str(uuid4())
            if manifest.idempotency_parameter:
                args[manifest.idempotency_parameter] = operation_id
            try:
                validate(args, manifest.parameters)
            except Exception:
                await self._emit("error", code="invalid_tool_arguments", tool=proposed.tool)
                blocked_calls += 1
                continue
            call = ToolCall(call_id=str(uuid4()), operation_id=operation_id, tool=proposed.tool,
                            arguments=args, dependencies=dependencies, effect=manifest.effect,
                            request_id=self.request_id)
            if call.effect == "write" and not self.authorization.allows(self._view(), call):
                await self._emit("clarify", text="This environment has not authorized that state-changing tool.")
                said_something = True
                continue
            self.dispatched[signature] = call.call_id
            self.attempt_counts[signature] = self.attempt_counts.get(signature, 0) + 1
            self.ledger[call.call_id] = call
            self.call_causes[call.call_id] = self.current_event_id
            self.state.status = "working"
            dispatched_any = True
            await self._emit("tool_call", **call.model_dump())
            self._spawn(self._execute(call, manifest.timeout_s))
        pending_now = any(c.status == "pending" for c in self.ledger.values())
        history_has_write = any(c.effect == "write" for c in self.ledger.values())
        # --- Outcome classification --------------------------------------------------
        # Every accepted plan is exactly one of: dispatched work (dispatched_any),
        # emitted an answer/clarification (said_something), legitimately waiting on
        # existing pending work (pending_now), or made no progress at all. Only the
        # last case needs a diagnostic and a bounded recovery attempt.
        write_owed_unmet = False
        if not proposal.calls and not pending_now and self.latest_complete:
            if history_has_write:
                pass  # A write call already exists in this session; unchanged prior behaviour.
            elif prior_write_owed and not proposal.clarification:
                # The accepted request still owes a state-changing effect. A completed read,
                # an omitted response, or a change of mind in this proposal's flags is
                # evidence, never a substitute for the effect: neither a prose claim nor
                # total silence may finish it.
                write_owed_unmet = True
            elif proposal.response:
                said_something = True
                await self._emit("final", text=proposal.response, basis="informational", backend="reasoner")
        if write_owed_unmet and not self.last_request_finished:
            # This proposal silently dropped the write intent a prior proposal established
            # for the same spoken request (e.g. write_requested=False on a follow-up, or an
            # empty plan). That is not new user evidence of cancellation, so restore intent
            # and give the reasoner one bounded corrective turn.
            self.write_intent_retained = True
            await self._emit("error", code="write_owed_not_progressed",
                             message="A requested state-changing effect is not complete; "
                                     "an empty or prose-only response cannot finish it.")
            await self._offer_recovery(self.write_stall_recoveries)
        elif ((self.latest_complete or final_correction) and not dispatched_any and not said_something
                and not pending_now and not self.last_request_finished
                and (repeated or blocked_calls
                     or (not proposal.calls and proposal.request_complete and not history_has_write))):
            # An empty plan on a request the model itself does not yet consider complete
            # (no calls, no clarification, request_complete=False) is legitimately still
            # awaiting more input (e.g. a spoken write request waiting on a promised
            # image) -- the same as partial speech, not a stall. Likewise, a write that
            # already exists elsewhere in this session keeps the prior informational-
            # answer restraint (see the pass branch above) rather than a new diagnostic.
            # Dropping this silently ends the turn with no output and nothing left to wake
            # the loop, so the session would otherwise stall until the scenario deadline.
            if repeated and not blocked_calls:
                await self._emit("error", code="repeated_completed_call", call_ids=sorted(set(repeated)),
                                 message="Every proposed call has already completed; its result is in evidence.")
                self.repeated_completed_call = True
                await self._offer_recovery(self.repeat_recoveries)
            elif repeated:
                # A mixed proposal: some calls already completed, others could not be
                # dispatched. "Every call is done" would misdescribe this turn.
                await self._emit("error", code="repeated_completed_call", call_ids=sorted(set(repeated)),
                                 message="Some proposed calls already completed and are in evidence; "
                                         "the rest could not be dispatched as proposed. Not every call is done.")
                self.repeated_completed_call = True
                await self._offer_recovery(self.repeat_recoveries)
            elif blocked_calls:
                await self._emit("error", code="no_dispatchable_call",
                                 message="None of the proposed calls could be dispatched as proposed; "
                                         "see the preceding errors for each one.")
                self.no_progress = True
                await self._offer_recovery(None)
            else:
                await self._emit("error", code="no_progress",
                                 message="The plan produced no tool call, clarification or answer; "
                                         "nothing else will advance this request.")
                self.no_progress = True
                await self._offer_recovery(None)

    def _argument_dependency_error(self, proposed, manifest):
        """Ground dynamic arguments in tracked state before read or write dispatch.

        This checks declared data dependencies; semantic context not represented in
        arguments must still be listed by the planner. No fuzzy alias/value inference.

        Conversational slots and ledger operation identity are separate namespaces.
        A status tool's lookup parameter (e.g. "receipt") is not a conversational
        slot, so it never lives in session.state.slots -- but the planner may still
        legitimately list that parameter name in `dependencies` to flag it as the
        value the call depends on. `ledger_dependencies` recognises that specific,
        narrow case: an unaliased argument whose value is exactly the operation_id
        of an unresolved write this manifest is the declared status_tool for. This
        does not create a slot and does not accept any other UUID-like string; a
        stale or unrelated operation id, or a name that is not this argument's own
        parameter name, still falls through to "missing_dependency" below.
        """
        properties = manifest.parameters.get("properties", {})
        unresolved_operations = {
            call.operation_id for call in self.ledger.values()
            if call.effect == "write" and call.status in {"unknown", "cancelled"}
            and self.manifests[call.tool].status_tool == manifest.name
        } if manifest.effect == "read" else set()
        ledger_dependencies = {
            name for name in proposed.dependencies
            if name not in self.state.slots
            and name not in proposed.argument_slots
            and isinstance(proposed.arguments.get(name), str)
            and proposed.arguments.get(name) in unresolved_operations
        }
        if any(name not in self.state.slots and name not in ledger_dependencies
               for name in proposed.dependencies):
            return "missing_dependency"
        if any(name not in proposed.arguments for name in proposed.argument_slots):
            return "argument_dependency_mismatch"
        for parameter, value in proposed.arguments.items():
            if parameter == manifest.idempotency_parameter:
                continue  # Replaced with the controller's stable operation identity.
            explicit_slot = proposed.argument_slots.get(parameter)
            if (manifest.effect == "write" and explicit_slot is not None
                    and explicit_slot != parameter and parameter in self._user_fixed_slots):
                # A17-1 alias bypass: the slot-provenance guard in _apply keys on
                # slot NAME, refusing a non-fresh proposal that rewrites
                # self.state.slots[name] for name in self._user_fixed_slots. A
                # planner can dodge that guard entirely without ever touching the
                # fixed slot: leave "day" alone, set a brand-new slot
                # ("chosen_day") to whatever value it likes, and use
                # argument_slots to point the write's "day" PARAMETER at that new
                # slot instead. Nothing above ever rewrites self.state.slots["day"],
                # so the _apply guard never fires -- but the call still ships a
                # "day" argument the user never authorized. A parameter name that
                # is itself a user-fixed slot denotes that slot's value by
                # definition; argument_slots may rename which slot backs a
                # parameter that was never fixed, but it may not redirect a
                # parameter whose own name the user already fixed onto a
                # different, unprotected slot. Self-aliasing (explicit_slot ==
                # parameter) is not a redirect and still falls through to the
                # ordinary grounding below.
                return "argument_dependency_mismatch"
            if explicit_slot is None:
                schema = properties.get(parameter, {})
                if isinstance(schema, dict):
                    # Inspect only direct constants here; the complete manifest is
                    # validated later with its original reference scope intact.
                    if "const" in schema or len(schema.get("enum", [])) == 1:
                        fixed = schema["const"] if "const" in schema else schema["enum"][0]
                        if Draft202012Validator({"const": fixed}).is_valid(value):
                            continue
                # Only an actual unresolved identity sent to its declared status
                # tool can be a ledger literal, regardless of that tool's arg name.
                if isinstance(value, str) and value in unresolved_operations:
                    continue
            slot_name = explicit_slot if explicit_slot is not None else parameter
            # Match the parameter's own name, never an alias target. ledger_dependencies
            # holds parameter names; slot_name holds a slot name for an aliased argument,
            # so comparing the two lets any parameter alias onto a ledger name and skip
            # grounding entirely.
            if explicit_slot is None and parameter in ledger_dependencies:
                continue
            slot = self.state.slots.get(slot_name)
            if slot is None or slot_name not in proposed.dependencies:
                return "missing_dependency"
            if not Draft202012Validator({"const": slot.value}).is_valid(value):
                return "argument_dependency_mismatch"
        return None

    async def _rollback_hypothesis(self, source):
        changed = set()
        if self.provisional_intent and self.provisional_intent[0] == source:
            self.state.intent = self.provisional_intent[1]
            self.provisional_intent = None
            self.state.revision += 1
        for name, (owner, prior) in list(self.provisional_slots.items()):
            if owner != source:
                continue
            del self.provisional_slots[name]
            changed.add(name)
            self.slot_revisions[name] = self.slot_revisions.get(name, 0) + 1
            if prior is None:
                self.state.slots.pop(name, None)
            else:
                self.state.slots[name] = prior.model_copy(update={"revision": self.slot_revisions[name]}, deep=True)
        if changed:
            self.state.revision += 1
            await self._invalidate_dependencies(changed, "hypothesis_replaced")

    async def _invalidate_dependencies(self, changed, reason):
        if "dependency_invalidation" in self.disabled:
            # Ablation: obsolete calls keep running and accepted reads stay in evidence.
            affected = [call.call_id for call in self.ledger.values()
                        if changed.intersection(call.dependencies)
                        and call.status in {"pending", "success"}]
            if affected:
                await self._emit("error", code="ablation_skipped_invalidation", reason=reason,
                                 slots=sorted(changed), call_ids=affected)
            return
        for call in list(self.ledger.values()):
            if not changed.intersection(call.dependencies):
                continue
            if call.status == "pending":
                await self._cancel(call, reason)
            elif call.effect == "read" and call.status == "success":
                # Previously accepted evidence can become obsolete after a correction.
                # Keep the call in the audit ledger but remove it from planning evidence.
                call.status = "stale"
                self.results = [result for result in self.results if result.call_id != call.call_id]

    def _corpus_lookup(self, call):
        """Blocking file I/O and lexical retrieval; never forwarded to the external executor.

        This runs OFF the event loop -- see _execute, which only ever calls it inside
        asyncio.to_thread -- so a slow disk or a large document cannot block input
        processing, acknowledgment or cancellation of anything else in the session (M2).
        Cheap argument-shape checks (query length) happen here too, before the
        potentially expensive read, rather than in the dispatcher.

        The "document" argument is model-supplied and untrusted: CorpusStore.read enforces
        the allowlist and refuses traversal/absolute names regardless of Start.corpus's own
        (already-validated) contents. The passage returned is opaque text in a ToolResult,
        entering evidence the same way any other read tool's result does.
        """
        document = call.arguments.get("document")
        query = call.arguments.get("query", "")
        if not is_safe_query(query):
            raise CorpusAccessError("query_too_long")
        text = self.corpus_store.read(document, self.corpus_allowlist)
        passage = best_passage(text, query)
        return ToolResult(call_id=call.call_id, status="success",
                          result={"document": document, "query": query, "passage": passage})

    async def _execute(self, call, timeout):
        if self._corpus_installed and call.tool == CORPUS_TOOL_NAME:
            if call.status != "pending":
                await self.inbox.put(WorkerMessage("tool", 0, ToolResult(call_id=call.call_id, status="cancelled")))
                return
            if self.corpus_store is None:
                await self.inbox.put(WorkerMessage("tool", 0,
                    ToolResult(call_id=call.call_id, status="failed", error="corpus_unavailable")))
                return
            # Bounded exactly like any external tool call below (same _bounded/timeout,
            # same exception-to-ToolResult conversion). Cancelling this await cannot stop
            # the underlying OS thread once asyncio.to_thread has started it -- Python
            # cannot preempt a running thread. What it DOES guarantee: the controller
            # stops waiting for that thread at the manifest's own timeout, and stale
            # cancellation/dependency-change is still enforced downstream in _result via
            # self.invalidated (matching every other tool call), so a passage the thread
            # eventually computes after the fact is dropped from evidence, never dispatched
            # a second time, and never blocks a later call for the same request.
            try:
                result = await self._bounded(asyncio.to_thread(self._corpus_lookup, call), timeout)
                if result.call_id != call.call_id:
                    raise ValueError("Corpus lookup returned wrong call ID")
            except CorpusAccessError as exc:
                result = ToolResult(call_id=call.call_id, status="failed", error=exc.code)
            except Exception as exc:
                result = ToolResult(call_id=call.call_id, status="failed", error=type(exc).__name__)
            await self.inbox.put(WorkerMessage("tool", 0, result))
            return
        if self.executor is not None and call.status != "pending":
            await self.inbox.put(WorkerMessage("tool", 0, ToolResult(call_id=call.call_id, status="cancelled")))
            return
        try:
            if self.executor is None:
                await self.clock.sleep(timeout)
                raise TimeoutError()
            result = await self._bounded(self.executor.execute(call.model_copy(deep=True)), timeout)
            if result.call_id != call.call_id:
                raise ValueError("Executor returned wrong call ID")
        except Exception as exc:
            result = ToolResult(call_id=call.call_id, status="unknown" if call.effect == "write" else "failed",
                                error=type(exc).__name__)
        await self.inbox.put(WorkerMessage("tool", 0, result))

    async def _cancel(self, call, reason):
        call.status = "cancelled"
        self.invalidated.add(call.call_id)
        await self._emit("cancel_call", call_id=call.call_id, operation_id=call.operation_id, reason=reason)
        # A call this controller services internally (the built-in corpus lookup) was
        # never given to self.executor and must never trigger ITS cancel() -- that would
        # notify an unrelated external tool about a call it never received (M3).
        if self.executor and not (self._corpus_installed and call.tool == CORPUS_TOOL_NAME):
            async def cancel():
                try:
                    status = await self._bounded(self.executor.cancel(call.call_id), 1)
                    if status == "cancelled_before_commit":
                        await self.inbox.put(WorkerMessage("tool", 0,
                            ToolResult(call_id=call.call_id, status="cancelled")))
                except Exception:
                    pass  # Cancellation is best effort; outcome remains unresolved.
            self._spawn(cancel())

    async def _cancel_writes(self, reason):
        for call in list(self.ledger.values()):
            if call.effect == "write" and call.status == "pending":
                await self._cancel(call, reason)

    async def _result(self, result):
        result = result.model_copy(deep=True)
        call = self.ledger.get(result.call_id)
        if call is None:
            await self._emit("error", code="unknown_call_result", call_id=result.call_id)
            return
        if call.effect == "write" and result.committed and call.status == "failed":
            # A failed/cancelled acknowledgment is not permission to discard later
            # evidence of a real effect. Keep that truth without completing a newer
            # request or undoing an explicit stop.
            call.status = "success"
            self.results.append(result.model_copy(update={"status": "success"}))
            self._results_admitted += 1
            await self._emit("error", code="effect_committed_after_invalidation"
                             if call.call_id in self.invalidated else "conflicting_write_outcome",
                             call_id=call.call_id, operation_id=call.operation_id,
                             previous_status="failed", result=result.result,
                             caused_by_event_id=self.call_causes[call.call_id],
                             message="The tool later confirmed an effect after reporting no effect.")
            return
        if call.status in {"success", "failed", "stale"}:
            return
        if call.effect == "write" and result.committed and result.status != "success":
            await self._emit("error", code="inconsistent_tool_result", call_id=call.call_id,
                             operation_id=call.operation_id, reported_status=result.status,
                             caused_by_event_id=self.call_causes[call.call_id],
                             message="The tool confirmed an effect despite a non-success response status.")
            result.status = "success"
        current = all(self.state.slots.get(key) and self.state.slots[key].revision == revision
                      for key, revision in call.dependencies.items())
        if call.call_id in self.invalidated or not current:
            if call.effect == "write" and result.committed:
                call.status = "success"
                self.results.append(result)
                self._results_admitted += 1
                await self._emit("error", code="effect_committed_after_invalidation", call_id=call.call_id,
                                 operation_id=call.operation_id, result=result.result,
                                 message="Cancellation did not roll back this effect.")
            elif result.status == "cancelled" or result.status == "failed":
                call.status = "failed"
                if call.effect == "write" and self.latest_complete and self.state.status != "stopped":
                    self._start_plan()
            elif call.effect == "read":
                call.status = "stale"
            else:
                call.status = "unknown"
                await self._emit("error", code="write_outcome_unknown", call_id=call.call_id)
            return
        if call.status == "unknown" and result.status == "unknown":
            return
        if call.effect == "read" and result.status == "unknown":
            result = result.model_copy(update={"status": "failed"})
        if call.effect == "write" and result.status == "success" and not result.committed:
            result = result.model_copy(update={"status": "unknown"})
        call.status = result.status if result.status != "cancelled" else "failed"
        if result.status == "unknown":
            self.state.status = "needs_reconciliation"
            await self._emit("error", code="write_outcome_unknown", call_id=call.call_id,
                             operation_id=call.operation_id, status_tool=self.manifests[call.tool].status_tool)
            # Status schema is dynamic; expose operation identity to the reasoner, which
            # can propose the declared read-only status tool. Never repeat the write.
            self.results.append(result)
            self._results_admitted += 1
            self._start_plan()
        elif result.status == "success":
            self.results.append(result)
            self._results_admitted += 1
            if call.effect == "write":
                self.state.status = "completed"
                self.last_request_finished = True
                await self._emit("final", result=result.result, call_id=call.call_id, operation_id=call.operation_id,
                                 basis="confirmed_tool_effect", caused_by_event_id=self.call_causes[call.call_id])
            else:
                await self._emit("acknowledge", result=result.result, call_id=call.call_id, basis="tool_evidence",
                                 caused_by_event_id=self.call_causes[call.call_id])
                await self._reconcile(call, result)
                self._start_plan()
        elif result.status == "failed":
            if call.effect == "write":
                self.last_request_finished = True
            await self._emit("error", code="tool_failed", call_id=call.call_id, detail=result.error)
            if call.effect == "read":
                # A failed read is planning evidence, not a dead end or a write
                # authorization. Let the reasoner correct its query, use the
                # existing one-retry budget, or explain the failure. Count this
                # admission just like successful results so failure-triggered
                # replanning cannot masquerade as fresh user speech.
                # Keep refused corpus contents and incidental failed-tool fields
                # out of the usable-result evidence channel.
                self.tool_failures.append(result.model_copy(update={"result": {}, "committed": False}, deep=True))
                del self.tool_failures[:-12]
                self._results_admitted += 1
                self._start_plan()

    async def _reconcile(self, status_call, result):
        """Executor-normalized status evidence, restricted to the manifest's status tool.

        Wire adapters must normalize real status schemas to operation_id/outcome. Never
        infer confirmation from arbitrary prose or let a model declare a write committed.
        """
        for original in self.ledger.values():
            if original.effect != "write" or original.status not in {"unknown", "cancelled"}:
                continue
            manifest = self.manifests[original.tool]
            if manifest.status_tool != status_call.tool:
                continue
            if result.result.get("operation_id") != original.operation_id:
                continue
            outcome = result.result.get("outcome")
            if outcome == "no_effect":
                original.status = "failed"
                self.state.status = "listening"
            elif outcome == "committed":
                original.status = "success"
                confirmed = ToolResult(call_id=original.call_id, status="success", committed=True,
                                       result=result.result)
                self.results.append(confirmed)
                self._results_admitted += 1
                if original.call_id in self.invalidated:
                    await self._emit("error", code="effect_committed_after_invalidation",
                                     call_id=original.call_id, result=result.result)
                else:
                    self.state.status = "completed"
                    self.last_request_finished = True
                    await self._emit("final", basis="reconciled_tool_effect", call_id=original.call_id,
                                     operation_id=original.operation_id, result=result.result,
                                     caused_by_event_id=self.call_causes[original.call_id])

    async def _shutdown(self, reason):
        if self.session_id is None:
            return
        for call in list(self.ledger.values()):
            if call.status == "pending":
                await self._cancel(call, reason)
        self.state.status = "ended"
        await self._emit("acknowledge", text="Session ended.", reason=reason)
