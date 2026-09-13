"""One authoritative controller; workers return messages and never edit session state."""

import asyncio
import json
from dataclasses import dataclass
from uuid import uuid4

from jsonschema import validate

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


class Agent:
    def __init__(self, perception, turn_policy, reasoner, executor=None, authorization=None,
                 scenario_timeout=115, inference_timeout=25, partial_debounce_s=0.08):
        if scenario_timeout <= 0 or inference_timeout <= 0 or partial_debounce_s < 0:
            raise ValueError("Timeouts must be positive and debounce nonnegative")
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
                           calls=[c.model_copy(deep=True) for c in self.ledger.values()])

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
            if self.latest_complete:
                await self._emit("acknowledge", text="I'll check that.", backend=obs.backend)
            # Partial plans may prepare reads but may never authorize writes.
            self._start_plan(source=key)
        elif message.kind == "plan":
            self.current_event_id = self.source_events.get(message.source)
            await self._apply(message.value, message.source)

    def _start_plan(self, source=None):
        self.generation += 1
        if source is not None:
            self.planning_source = source
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
                await self.inbox.put(WorkerMessage("plan", generation, proposal.model_copy(deep=True), source=source))
            except Exception as exc:
                await self.inbox.put(WorkerMessage("failure", generation, type(exc).__name__))
        self.planner = self._spawn(plan())

    async def _apply(self, proposal: PlanProposal, source=None):
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
            # Only the current spoken request can supply write intent. An image
            # may fill missing details, but cannot invent or revive that intent.
            self.speech_write_requested = bool(self.speech_ready and proposal.write_requested
                                               and not proposal.clarification)
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
        if proposal.clarification and (self.latest_complete or final_correction):
            self.state.status = "clarifying"
            await self._emit("clarify", text=proposal.clarification)
        for proposed in proposal.calls:
            manifest = self.manifests.get(proposed.tool)
            if not manifest:
                await self._emit("error", code="unknown_tool", tool=proposed.tool)
                continue
            if any(name not in self.state.slots for name in proposed.dependencies):
                await self._emit("error", code="missing_dependency")
                continue
            if manifest.effect == "write":
                if not (self.latest_complete and self.speech_ready and self.speech_write_requested
                        and proposal.request_complete and proposal.write_requested
                        and not self.state.correction_pending and not proposal.clarification):
                    continue
                if any(not self.state.slots[name].confirmed for name in proposed.dependencies):
                    continue
                # Unknown/cancelled writes may have committed: no new write until reconciled.
                if any(c.effect == "write" and c.status in {"unknown", "cancelled"} for c in self.ledger.values()):
                    await self._emit("clarify", text="The earlier action has an unresolved outcome; check its status first.")
                    continue
            dependencies = {name: self.state.slots[name].revision for name in proposed.dependencies}
            signature = json.dumps([self.request_id, proposed.tool, proposed.arguments, dependencies], sort_keys=True)
            previous = self.ledger.get(self.dispatched.get(signature))
            if previous and (previous.status != "failed" or self.attempt_counts[signature] >= 2):
                continue
            operation_id = previous.operation_id if previous else str(uuid4())
            args = dict(proposed.arguments)
            if manifest.idempotency_parameter:
                args[manifest.idempotency_parameter] = operation_id
            try:
                validate(args, manifest.parameters)
            except Exception:
                await self._emit("error", code="invalid_tool_arguments", tool=proposed.tool)
                continue
            call = ToolCall(call_id=str(uuid4()), operation_id=operation_id, tool=proposed.tool,
                            arguments=args, dependencies=dependencies, effect=manifest.effect)
            if call.effect == "write" and not self.authorization.allows(self._view(), call):
                await self._emit("clarify", text="This environment has not authorized that state-changing tool.")
                continue
            self.dispatched[signature] = call.call_id
            self.attempt_counts[signature] = self.attempt_counts.get(signature, 0) + 1
            self.ledger[call.call_id] = call
            self.call_causes[call.call_id] = self.current_event_id
            self.state.status = "working"
            await self._emit("tool_call", **call.model_dump())
            self._spawn(self._execute(call, manifest.timeout_s))
        if proposal.response and not proposal.calls and not self.state.pending_call_ids and self.latest_complete:
            if not any(c.effect == "write" for c in self.ledger.values()):
                await self._emit("final", text=proposal.response, basis="informational", backend="reasoner")

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
