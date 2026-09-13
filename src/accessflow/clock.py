import asyncio
import time


class RealClock:
    def now(self) -> float:
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class ManualClock:
    """Advance only from a test; sleepers wake on the same event-loop turn."""

    def __init__(self):
        self.time = 0.0
        self.waiters = []

    def now(self):
        return self.time

    async def sleep(self, seconds):
        future = asyncio.get_running_loop().create_future()
        self.waiters.append((self.time + seconds, future))
        try:
            await future
        finally:
            self.waiters = [(at, f) for at, f in self.waiters if f is not future]

    def advance(self, seconds):
        if seconds < 0:
            raise ValueError("Clock cannot go backwards")
        self.time += seconds
        for at, future in self.waiters:
            if at <= self.time and not future.done():
                future.set_result(None)
