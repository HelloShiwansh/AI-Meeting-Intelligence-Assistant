"""Small source controls for chat; no changes to the surrounding page layout."""

import math
from pathlib import Path

import streamlit as st


def render_chat_sources(message: dict, message_index: int, playback=None):
    citations = message.get("citations", [])
    if message.get("citation_notice"):
        st.caption(message["citation_notice"])
    if not citations:
        return
    with st.expander(f"Sources · {len(citations)}", icon=":material/format_quote:"):
        for citation in citations:
            st.markdown(f"**{citation['id']} · {citation['label']}**")
            if citation["timing_precision"] != "segment":
                st.caption("Approximate audio passage; this is not sentence-level timing.")
            st.text(citation["text"])
            if citation.get("url"):
                st.link_button("Open this moment on YouTube", citation["url"])
            elif playback:
                if st.button(
                    f"Play from {citation['label']}", icon=":material/play_arrow:",
                    key=f"citation_{message_index}_{citation['id']}",
                ):
                    st.session_state.chat_playback = {
                        "start_seconds": math.floor(citation["start_seconds"]),
                        "label": citation["label"],
                    }


def render_chat_playback(playback):
    selected = st.session_state.get("chat_playback")
    if not selected or not playback:
        return
    with st.expander(f"Source playback · {selected['label']}", expanded=True):
        data = playback.get("data") if "data" in playback else playback["path"]
        extension = Path(playback["name"]).suffix.lower()
        try:
            if extension in {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}:
                st.video(
                    data, start_time=selected["start_seconds"],
                    format={".webm": "video/webm", ".mov": "video/quicktime"}.get(extension, "video/mp4"),
                    alt="Original video at the cited passage",
                )
            else:
                mime = {
                    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
                    ".aac": "audio/aac", ".ogg": "audio/ogg", ".opus": "audio/ogg", ".flac": "audio/flac",
                }.get(extension, "audio/wav")
                st.audio(data, format=mime, start_time=selected["start_seconds"], alt="Original audio at the cited passage")
            st.caption("Playback depends on your browser supporting the original media format.")
        except (OSError, ValueError):
            st.info("This media is no longer available for playback. The cited text and timestamp are still shown in Sources.")
