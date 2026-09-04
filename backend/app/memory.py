"""Memory — trend analysis across runs, instead of judging each run in isolation.

Every run's evidence is already durably stored (`store.insert_evidence`); this
module is the read-side that turns that history into a per-vehicle, per-signal
trend (e.g. cargo_temperature climbing over the last 4 runs), which is a much
stronger signal in a demo than a single snapshot.
"""
from __future__ import annotations

from .schemas import TrendPoint, VehicleTrend
from .store import Store

_RISE_EPSILON = 1e-6


class TrendEngine:
    def __init__(self, store: Store) -> None:
        self._store = store

    def trend(self, vehicle_id: str, signal: str, limit: int = 8) -> VehicleTrend:
        decisions = self._store.list_recent_decisions(limit=max(limit * 3, 20))
        points: list[TrendPoint] = []
        for d in decisions:
            if d.get("vehicle_id") != vehicle_id:
                continue
            for ev in d.get("trace", {}).get("evidence_snapshot", []):
                if ev.get("signal") == signal:
                    points.append(TrendPoint(
                        run_id=d["run_id"], timestamp=ev["timestamp"], value=ev["value"],
                    ))
                    break
            if len(points) >= limit:
                break
        points.reverse()  # oldest -> newest

        direction = "insufficient_data"
        delta = None
        if len(points) >= 2:
            delta = round(points[-1].value - points[0].value, 3)
            if delta > _RISE_EPSILON:
                direction = "rising"
            elif delta < -_RISE_EPSILON:
                direction = "falling"
            else:
                direction = "flat"

        return VehicleTrend(vehicle_id=vehicle_id, signal=signal, points=points,
                            direction=direction, delta=delta)
