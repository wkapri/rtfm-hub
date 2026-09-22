import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger("hubapp.trace")


@dataclass
class TraceStep:
    name: str
    detail: str
    duration_ms: int


@dataclass
class _StepHandle:
    """Yielded from Trace.step() so the caller can attach a human-readable detail
    (e.g. "tavily: 5 results") once it's known, partway through the block."""

    name: str
    detail: str = ""


@dataclass
class Trace:
    """Records the sequence of steps behind one request — which search backend
    ran, what it found, whether a PDF passed the relevance check, how long each
    part took — so an admin-facing UI can show what actually happened instead of
    a black box. Every step is also logged server-side as it completes, so the
    same information is available from the server console even without the UI.
    """

    steps: list[TraceStep] = field(default_factory=list)

    @contextmanager
    def step(self, name: str) -> Iterator[_StepHandle]:
        handle = _StepHandle(name=name)
        start = time.perf_counter()
        try:
            yield handle
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000)
            self.steps.append(TraceStep(name=name, detail=handle.detail, duration_ms=duration_ms))
            suffix = f" — {handle.detail}" if handle.detail else ""
            logger.info("[trace] %s (%dms)%s", name, duration_ms, suffix)
