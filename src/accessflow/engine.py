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


class Agent:
    def __init__(self, perception, turn_policy, reasoner, executor=None, authorization=None,
                 scenario_timeout=115, inference_timeout=25):
        self.perception = perception
        self.turn_policy = turn_policy
        self.reasoner = reasoner
        self.executor = executor
        self.authorization = authorization or DenyWrites()
        self.scenario_timeout = min(scenario_timeout, 119)
        self.inference_timeout = inference_timeout
        self.running = False

    async def run(self, input_queue, output_queue, clock=None):
        if self.running:
            raise RuntimeError("Use a separate Agent instance for each concurrent session")
        self.running = True
        self.clock = clock or RealClock()
        self.out = output_queue
        self.inbox = asyncio.Queue()
        self.workers = set()
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
        self.last_sequence = -1
        self.invalidated = set()

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
                    self.manifests = {tool.name: tool for tool in event.payload.tools}
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
                    self.latest_complete = False
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
                        self.active_frame = payload.frame_id
                    else:
                        source = ("speech", payload.utterance_id)
                        revision = payload.revision
                    if revision <= self.sources.get(source, -1):
                        continue
                    self.sources[source] = revision
                    if self.last_request_finished:
                        self.request_id = str(uuid4())
                        self.last_request_finished = False
                    self.generation += 1
                    self.latest_complete = False
                    self.state.correction_pending = True
                    self.state.status = "listening"
                    # Conservative write guard until semantic/dependency resolution.
                    await self._cancel_writes("new_evidence")
                    self._spawn(self._perceive(event, self.generation))
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

    async def _perceive(self, event, generation):
        async def collect():
            async for observation in self.perception.observe(event):
                await self.inbox.put(WorkerMessage("observation", generation, observation))
        try:
            await self._bounded(collect(), self.inference_timeout)
        except Exception as exc:
            await self.inbox.put(WorkerMessage("failure", generation, type(exc).__name__))

    def _view(self):
        self.state.pending_call_ids = [c.call_id for c in self.ledger.values() if c.status == "pending"]
        return SessionView(session_id=self.session_id, state=self.state.model_copy(deep=True),
                           observations=list(self.observations.values())[-24:],
                           results=[r.model_copy(deep=True) for r in self.results[-12:]])

    async def _emit(self, kind, **payload):
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
            obs: Observation = message.value
            key = ("image" if obs.modality == "image" else "speech", obs.source_id)
            if self.sources.get(key) != obs.revision:
                return
            if obs.modality == "image" and obs.source_id != self.active_frame:
                return
            self.observations[key] = obs
            decision = self.turn_policy.update(obs, self._view())
            if obs.modality != "image":
                self.latest_complete = decision.kind == "complete" and obs.final
            else:
                speech = [o for o in self.observations.values() if o.modality != "image"]
                self.latest_complete = bool(speech and speech[-1].final)
            self.state.correction_pending = not self.latest_complete
            if decision.kind == "stop":
                await self._cancel_writes("explicit_stop")
                self.state.status = "stopped"
                await self._emit("acknowledge", text="Stopped.", stop_output=True)
                return
            if decision.kind == "backchannel":
                return
            if self.latest_complete:
                await self._emit("acknowledge", text="I'll check that.", backend=obs.backend)
            # Partial plans may prepare reads but may never authorize writes.
            self._start_plan()
        elif message.kind == "plan":
            await self._apply(message.value)

    def _start_plan(self):
        if self.planner and not self.planner.done():
            self.planner.cancel()
        view = self._view()
        generation = self.generation

        async def plan():
            try:
                proposal = await self._bounded(self.reasoner.plan(view, list(self.manifests.values())),
                                               self.inference_timeout)
                await self.inbox.put(WorkerMessage("plan", generation, proposal))
            except Exception as exc:
                await self.inbox.put(WorkerMessage("failure", generation, type(exc).__name__))
        self.planner = self._spawn(plan())

    async def _apply(self, proposal: PlanProposal):
        changed = set()
        for name, value in proposal.slot_updates.items():
            old = self.state.slots.get(name)
            if old is None or old.value != value:
                changed.add(name)
                self.state.slots[name] = Slot(value=value, confirmed=self.latest_complete,
                                              revision=(old.revision + 1 if old else 1),
                                              evidence=[o.event_id for o in self.observations.values()])
            elif self.latest_complete:
                old.confirmed = True
        if changed or proposal.intent != self.state.intent:
            self.state.revision += 1
        if proposal.intent is not None:
            self.state.intent = proposal.intent
        for call in list(self.ledger.values()):
            if call.status == "pending" and changed.intersection(call.dependencies):
                await self._cancel(call, "dependency_changed")
        if proposal.clarification and self.latest_complete:
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
                if not (self.latest_complete and proposal.request_complete and proposal.write_requested
                        and not self.state.correction_pending):
                    continue
                if any(not self.state.slots[name].confirmed for name in proposed.dependencies):
                    continue
                # Unknown/cancelled writes may have committed: no new write until reconciled.
                if any(c.effect == "write" and c.status in {"unknown", "cancelled"} for c in self.ledger.values()):
                    await self._emit("clarify", text="The earlier action has an unresolved outcome; check its status first.")
                    continue
            dependencies = {name: self.state.slots[name].revision for name in proposed.dependencies}
            signature = json.dumps([self.request_id, proposed.tool, proposed.arguments, dependencies], sort_keys=True)
            if signature in self.dispatched:
                continue
            operation_id = str(uuid4())
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
            self.ledger[call.call_id] = call
            self.state.status = "working"
            await self._emit("tool_call", **call.model_dump())
            self._spawn(self._execute(call, manifest.timeout_s))
        if proposal.response and not proposal.calls and not self.state.pending_call_ids and self.latest_complete:
            if not any(c.effect == "write" for c in self.ledger.values()):
                await self._emit("final", text=proposal.response, basis="informational", backend="reasoner")

    async def _execute(self, call, timeout):
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
        call = self.ledger.get(result.call_id)
        if call is None:
            await self._emit("error", code="unknown_call_result", call_id=result.call_id)
            return
        if call.status in {"success", "failed", "stale"}:
            return
        current = all(self.state.slots.get(key) and self.state.slots[key].revision == revision
                      for key, revision in call.dependencies.items())
        if call.status == "cancelled" or not current:
            if call.effect == "write" and result.committed:
                call.status = "success"
                self.results.append(result)
                await self._emit("error", code="effect_committed_after_invalidation", call_id=call.call_id,
                                 result=result.result, message="Cancellation did not roll back this effect.")
            elif result.status == "cancelled" or result.status == "failed":
                call.status = "failed"
            elif call.effect == "read":
                call.status = "stale"
            else:
                call.status = "unknown"
                await self._emit("error", code="write_outcome_unknown", call_id=call.call_id)
            return
        if call.status == "unknown" and result.status == "unknown":
            return
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
                await self._emit("final", result=result.result, call_id=call.call_id, basis="confirmed_tool_effect")
            else:
                await self._emit("acknowledge", result=result.result, call_id=call.call_id, basis="tool_evidence")
                await self._reconcile(call, result)
                self._start_plan()
        elif result.status == "failed":
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
                                     result=result.result)

    async def _shutdown(self, reason):
        for call in list(self.ledger.values()):
            if call.status == "pending":
                await self._cancel(call, reason)
        self.state.status = "ended"
        await self._emit("acknowledge", text="Session ended.", reason=reason)
