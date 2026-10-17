"""Compatibility helpers; pass shared analysis to avoid repeated model calls."""

from core.analysis import analyze_meeting


def extract_action_items(transcript: str, *, analysis: dict | None = None) -> str:
    return (analysis if analysis is not None else analyze_meeting(transcript))["action_items"]


def extract_key_decisions(transcript: str, *, analysis: dict | None = None) -> str:
    return (analysis if analysis is not None else analyze_meeting(transcript))["key_decisions"]


def extract_questions(transcript: str, *, analysis: dict | None = None) -> str:
    return (analysis if analysis is not None else analyze_meeting(transcript))["open_questions"]
