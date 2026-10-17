"""Timestamped speech data shared by transcription and retrieval."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start_seconds: float
    end_seconds: float
    timing_precision: str = "segment"

    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("A transcript segment needs text.")
        if not all(isfinite(t) for t in (self.start_seconds, self.end_seconds)):
            raise ValueError("Transcript times must be finite.")
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("Transcript times must be positive, ordered ranges.")
        if self.timing_precision not in {"segment", "passage", "chunk"}:
            raise ValueError("Unknown timestamp precision.")


@dataclass(frozen=True)
class TimestampedTranscript:
    segments: tuple[TranscriptSegment, ...]

    @property
    def text(self) -> str:
        return " ".join(segment.text.strip() for segment in self.segments)
