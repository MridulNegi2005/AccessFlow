"""LiveKit Inference planner for the optional FDB-v3 voice adapter."""

from __future__ import annotations

import json
import os
import time
from collections import deque

from livekit.agents import APIConnectOptions, inference, llm


class LiveKitPlannerBackend:
    def __init__(self, model: str = "openai/gpt-5.6-luna", *, client=None):
        self.model = model
        self.client = client or inference.LLM(
            model=model,
            api_key=os.environ["LIVEKIT_API_KEY"],
            api_secret=os.environ["LIVEKIT_API_SECRET"],
        )
        self._requests: deque[dict] = deque(maxlen=128)

    @property
    def name(self) -> str:
        return f"livekit/{self.model}"

    def evidence(self) -> dict:
        return {"backend": "livekit", "model": self.model,
                "response_format": "json_object", "requests": list(self._requests)}

    async def generate(self, system, data, schema, **_):
        started = time.monotonic()
        context = llm.ChatContext()
        context.add_message(role="system", content=system)
        context.add_message(
            role="user",
            content=json.dumps(data, ensure_ascii=False, separators=(",", ":"))
            + "\nJSON schema:\n" + json.dumps(schema, separators=(",", ":")),
        )
        pieces = []
        usage = {}
        try:
            stream = self.client.chat(
                chat_ctx=context,
                conn_options=APIConnectOptions(timeout=30.0, max_retry=1),
                extra_kwargs={"response_format": {"type": "json_object"}},
            )
            async with stream:
                async for chunk in stream:
                    if chunk.delta and chunk.delta.content:
                        pieces.append(chunk.delta.content)
                    if chunk.usage:
                        usage = {"prompt_tokens": chunk.usage.prompt_tokens,
                                 "completion_tokens": chunk.usage.completion_tokens}
            result = json.loads("".join(pieces))
        except Exception as error:
            self._requests.append({
                "outcome": "failure", "seconds": round(time.monotonic() - started, 2),
                "exception_type": type(error).__name__,
                "status_code": getattr(error, "status_code", None),
            })
            raise
        self._requests.append({
            "outcome": "success", "seconds": round(time.monotonic() - started, 2), **usage,
        })
        return result

    async def aclose(self) -> None:
        await self.client.aclose()
