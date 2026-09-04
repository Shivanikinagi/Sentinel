"""RetryEngine — bounded, backoff-capable retry around a single flaky call.

Distinct from the CircuitBreaker: the breaker decides whether a call should be
attempted AT ALL, tracking failures *across* runs; the RetryEngine decides
whether to try the SAME call again *within* one run, before the breaker ever
sees a final failure. Today the only wrapped call is the Risk Assessment
Engine (critic) backend request — the one call in the harness that crosses a
real network boundary.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class RetryOutcome(Generic[T]):
    result: T | None
    attempts: int
    succeeded: bool
    last_error: str | None = None


class RetryEngine:
    def __init__(self, max_attempts: int = 2, backoff_seconds: float = 0.0) -> None:
        self.max_attempts = max(1, max_attempts)
        self.backoff_seconds = backoff_seconds

    def run(self, func: Callable[[], T],
            is_retryable: Callable[[T], bool] = lambda _: False) -> RetryOutcome[T]:
        """Call `func()` up to `max_attempts` times. Retries when `func()` raises,
        OR when it returns a result `is_retryable()` flags as a transient
        failure (needed here because the Critic never raises — a backend error
        is turned into a rejected CriticResult, not an exception)."""
        result: T | None = None
        last_error: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = func()
            except Exception as exc:  # noqa: BLE001 - any backend failure is retryable
                last_error = f"{exc.__class__.__name__}: {exc}"
                if attempt < self.max_attempts:
                    if self.backoff_seconds:
                        time.sleep(self.backoff_seconds)
                    continue
                return RetryOutcome(result=None, attempts=attempt, succeeded=False,
                                    last_error=last_error)

            if not is_retryable(result) or attempt >= self.max_attempts:
                return RetryOutcome(result=result, attempts=attempt, succeeded=True)
            if self.backoff_seconds:
                time.sleep(self.backoff_seconds)

        return RetryOutcome(result=result, attempts=self.max_attempts,
                            succeeded=result is not None, last_error=last_error)
