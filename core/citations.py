"""Validate model-selected evidence and render times from trusted metadata."""

import math
import re
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field

FALLBACK_ANSWER = "I could not find this information in the meeting transcript."


class CitedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1, max_length=4)


class CitedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    found: bool
    claims: list[CitedClaim] = Field(max_length=20)


def format_time(seconds: float) -> str:
    seconds = max(0, math.floor(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def timestamp_label(start: float, end: float, precision: str) -> str:
    label = f"{format_time(start)}–{format_time(math.ceil(end))}"
    return f"≈ {label}" if precision != "segment" else label


def youtube_timestamp_url(source: str, start: float) -> str | None:
    """Canonicalize known YouTube URLs; never link arbitrary retrieved URLs."""
    parsed = urlparse(source)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    parts = parsed.path.strip("/").split("/")
    video_id = None
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif len(parts) > 1 and parts[0] in {"shorts", "embed", "live"}:
            video_id = parts[1]
    if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return f"https://www.youtube.com/watch?v={video_id}&t={max(0, math.floor(start))}s"
    return None


def citation_sources(docs) -> dict[str, dict]:
    """Only timestamped, retrieved passages are eligible citation targets."""
    sources = {}
    for doc in docs:
        metadata = doc.metadata
        start, end = metadata.get("start_seconds"), metadata.get("end_seconds")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            continue
        precision = metadata.get("timing_precision")
        if precision not in {"segment", "passage", "chunk"}:
            continue
        source_id = f"S{len(sources) + 1}"
        sources[source_id] = {
            "id": source_id, "video_id": metadata.get("video_id", ""),
            "start_seconds": start, "end_seconds": end,
            "timing_precision": precision,
            "label": timestamp_label(start, end, precision),
            "text": doc.page_content,
            "url": youtube_timestamp_url(metadata.get("source_url", ""), start),
        }
    return sources


def render_cited_answer(raw: str, sources: dict[str, dict]) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
    parsed = CitedAnswer.model_validate_json(text)
    if not parsed.found:
        if parsed.claims:
            raise ValueError("An unanswered question must not include claims.")
        return {"answer": FALLBACK_ANSWER, "citations": []}
    if not parsed.claims:
        raise ValueError("A found answer must contain cited claims.")
    paragraphs, used = [], {}
    for claim in parsed.claims:
        if not claim.text.strip():
            raise ValueError("Empty answer claim.")
        # Models select IDs; they must not manufacture timestamp/source labels.
        if re.search(r"\[S\d+\]|\[\d+:\d+", claim.text):
            raise ValueError("Put evidence IDs in source_ids, not in claim text.")
        references = []
        for source_id in dict.fromkeys(claim.source_ids):
            if source_id not in sources:
                raise ValueError(f"Unknown citation source: {source_id}")
            source = sources[source_id]
            used[source_id] = source
            label = source["label"]
            references.append(f"[{label}]({source['url']})" if source["url"] else f"[{label}]")
        paragraphs.append(claim.text.strip() + " " + " ".join(references))
    return {"answer": "\n\n".join(paragraphs), "citations": list(used.values())}
