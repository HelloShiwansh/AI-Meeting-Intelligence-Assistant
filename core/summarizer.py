"""Compatibility helpers; share one analyze_meeting() result across outputs."""

from core.analysis import analyze_meeting, split_transcript


def summarize(transcript: str, *, analysis: dict | None = None) -> str:
    return (analysis if analysis is not None else analyze_meeting(transcript))["summary"]


def generate_title(transcript: str, *, analysis: dict | None = None) -> str:
    return (analysis if analysis is not None else analyze_meeting(transcript))["title"]
