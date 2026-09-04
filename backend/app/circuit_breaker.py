"""Circuit Breaker Pattern for LLM Critic API requests.

Tracks consecutive network/LLM failures. When failures exceed the threshold (default 3),
the circuit OPENS and trips to deterministic fallback without waiting for network timeouts.
"""
from __future__ import annotations

import time
from typing import Any, Callable


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = "HALF-OPEN"
                return False
            return True
        return False

    def execute(self, func: Callable[[], Any]) -> Any:
        if self.is_open():
            raise CircuitOpenError(
                f"LLM Circuit Breaker is OPEN due to {self.failure_count} consecutive failures. Using deterministic fallback."
            )

        try:
            result = func()
            if self.state == "HALF-OPEN":
                self.reset()
            return result
        except Exception as exc:
            self.record_failure()
            raise exc

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def reset(self) -> None:
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"


_GLOBAL_CIRCUIT_BREAKER = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    return _GLOBAL_CIRCUIT_BREAKER
