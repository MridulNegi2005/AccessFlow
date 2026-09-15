"""One authoritative controller; workers return messages and never edit session state."""

import asyncio
import json
from dataclasses import dataclass
from uuid import uuid4

from jsonschema import Draft202012Validator, validate
from jsonschema.exceptions import ValidationError as PlanSchemaViolation

from .clock import RealClock
from .contracts import (
    AudioEvent, EndEvent, FrameEvent, InterruptEvent, Observation, OutputEvent,
    PlanProposal, ResultEvent, SessionView, Slot, Snapshot, StartEvent, ToolCall,
    ToolResult, TranscriptEvent,
)


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
                 disabled=()):
        if scenario_timeout <= 0 or inference_timeout <= 0 or partial_debounce_s < 0:
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
        self.ledger = {}
        self.seen = set()
        self.dispatched = {}
        self.generation = 0
        self.request_id = str(uuid4())
        self.last_request_finished = False
        self.output_sequence = 0
        self.latest_complete = False
        self.planner = None
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
        self.speech_write_requested = False
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
                    self.speech_write_requested = False
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
                        self.speech_write_requested = False
                        self.semantic_correction_event = None
                    if self.last_request_finished:
                        self.request_id = str(uuid4())
                        self.last_request_finished = False
                        self.speech_write_requested = False
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
                           calls=[c.model_copy(deep=True) for c in self.ledger.values()],
                           write_pending=self.speech_write_requested,
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
                self.latest_complete = (self.speech_ready or self.active_speech is None) and (
                    obs.final and decision.kind == "complete")
            self.state.correction_pending = not self.latest_complete
            if decision.kind == "stop":
                self.generation += 1
                self.perception_epoch += 1
                await self._cancel_writes("explicit_stop")
                self.state.status = "stopped"
                await self._emit("acknowledge", text="Stopped.", stop_output=True)
                return
            if decision.kind == "backchannel":
                return
            if self.latest_complete or (obs.final and decision.kind == "possible_correction"):
                # A final correction can be acknowledged while semantics are still
                # unresolved. This does not mark the request complete or authorize
                # a write; partial speech continues without an interjection.
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
        source = self.planning_source
        if self.planner and not self.planner.done():
            self.planner.cancel()
        view = self._view()
        generation = self.generation

        async def plan():
            try:
                if view.state.correction_pending and self.partial_debounce_s:
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
        # Snapshot before this proposal can mutate speech_write_requested below. Mirrors
        # ModelReasoner.write_outstanding: true when the CURRENT request's spoken write
        # request names a real write tool that has not been dispatched or confirmed by
        # any call the current request has made yet. Scoped to self.request_id so an
        # old, unrelated write earlier in the session cannot silently satisfy (or
        # continuation-block) a brand new request -- see ToolCall.request_id.
        prior_write_owed = (self.speech_write_requested
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
            # Only the current spoken request can supply write intent. A genuinely
            # new utterance/hypothesis (fresh_evidence) is authoritative either way,
            # matching prior behaviour: it can newly recognise intent or retract it
            # (an explicit correction/cancellation is new user evidence).
            #
            # A plan triggered by a tool result for this same request
            # (fresh_evidence=False) may still newly RECOGNISE intent it had not
            # seen before (e.g. deciding to book only after reading support notes),
            # which is why read-then-write continuations work. What it must not do
            # is ERASE already-recognised intent just because this follow-up omits
            # or flips the flag -- that is not new user evidence, only a change of
            # mind by the same model on the same evidence. See the request
            # lifecycle note on ToolCall.request_id.
            if fresh_evidence:
                self.speech_write_requested = bool(self.speech_ready and proposal.write_requested
                                                   and not proposal.clarification)
            elif proposal.write_requested and self.speech_ready and not proposal.clarification:
                self.speech_write_requested = True
        changed = set()
        for name, value in proposal.slot_updates.items():
            old = self.state.slots.get(name)
            if not self.latest_complete and name not in self.provisional_slots:
                self.provisional_slots[name] = (source,
                                                old.model_copy(deep=True) if old else None)
            elif not self.latest_complete and self.provisional_slots[name][0] != source:
                self.provisional_slots[name] = (source, self.provisional_slots[name][1])
            elif self.latest_complete:
                self.provisional_slots.pop(name, None)
            if old is None or old.value != value:
                changed.add(name)
                self.slot_revisions[name] = self.slot_revisions.get(name, 0) + 1
                self.state.slots[name] = Slot(value=value, confirmed=self.latest_complete,
                                              revision=self.slot_revisions[name],
                                              evidence=[o.event_id for o in self.observations.values()])
            elif self.latest_complete:
                old.confirmed = True
        if changed or (proposal.intent is not None and proposal.intent != self.state.intent):
            self.state.revision += 1
        if proposal.intent is not None:
            if not self.latest_complete and self.provisional_intent is None:
                self.provisional_intent = (source, self.state.intent)
            elif self.latest_complete:
                self.provisional_intent = None
            self.state.intent = proposal.intent
        await self._invalidate_dependencies(changed, "dependency_changed")
        said_something = bool(proposal.clarification)
        if proposal.clarification and (self.latest_complete or final_correction):
            self.state.status = "clarifying"
            await self._emit("clarify", text=proposal.clarification)
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
                if not (self.latest_complete and self.speech_ready and self.speech_write_requested
                        and proposal.request_complete and proposal.write_requested
                        and not self.state.correction_pending and not proposal.clarification):
                    blocked_calls += 1
                    continue
                if any(not self.state.slots[name].confirmed for name in proposed.dependencies):
                    blocked_calls += 1
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
            self.speech_write_requested = True
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

    async def _execute(self, call, timeout):
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
        if self.executor:
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
            self._start_plan()
        elif result.status == "success":
            self.results.append(result)
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
