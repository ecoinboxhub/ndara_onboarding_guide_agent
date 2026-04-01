"""
Quality metrics collection for the voice agent.
Stores turn latency, turn count, and call completion data for health and diagnostics.
Extensible to Prometheus or other backends.
"""

from typing import Dict, Any, List


class QualityMetrics:
    def __init__(self, config) -> None:
        self.config = config
        self._latest_status: Dict[str, Any] = {}
        self._turn_metrics: List[Dict[str, Any]] = []
        self._call_completions: List[Dict[str, Any]] = []
        self._max_stored = 1000  # Limit stored entries

    def record_call_status(self, call_sid: str, status: str, duration: str | None) -> None:
        self._latest_status[call_sid] = {"status": status, "duration": duration}

    def record_turn(
        self,
        call_id: str,
        turn_count: int,
        transcript_length: int,
        processing_time: float,
    ) -> None:
        entry = {
            "call_id": call_id,
            "turn_count": turn_count,
            "transcript_length": transcript_length,
            "processing_time_sec": round(processing_time, 3),
        }
        self._turn_metrics.append(entry)
        if len(self._turn_metrics) > self._max_stored:
            self._turn_metrics = self._turn_metrics[-self._max_stored:]

    def record_call_completion(
        self,
        call_sid: str,
        duration_seconds: float | None,
        turn_count: int,
    ) -> None:
        entry = {
            "call_sid": call_sid,
            "duration_seconds": duration_seconds,
            "turn_count": turn_count,
        }
        self._call_completions.append(entry)
        if len(self._call_completions) > self._max_stored:
            self._call_completions = self._call_completions[-self._max_stored:]

    def get_metrics(self) -> Dict[str, Any]:
        turns = self._turn_metrics[-100:] if self._turn_metrics else []
        completions = self._call_completions[-50:] if self._call_completions else []
        avg_latency = None
        if turns:
            latencies = [t["processing_time_sec"] for t in turns]
            avg_latency = round(sum(latencies) / len(latencies), 3)
        return {
            "latest_status": self._latest_status,
            "recent_turns": turns,
            "recent_completions": completions,
            "avg_turn_latency_sec": avg_latency,
        }


