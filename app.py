"""A friendly workspace for turning videos into useful meeting notes."""

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from utils.exports import RESULT_SECTIONS, build_downloads, export_filename
from utils.uploads import MEDIA_EXTENSIONS, media_source
from utils.chat_citations import render_chat_sources, render_chat_playback

load_dotenv()
st.set_page_config(
    page_title="GetNote",
    page_icon=":material/play_circle:",
    layout="wide",
    initial_sidebar_state="expanded",
)

for key, default in {
    "result": None,
    "chat_history": [],
    "pipeline_done": False,
    "pipeline_steps": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

STEPS = {
    "audio": "Prepare the audio",
    "transcript": "Write the transcript",
    "analysis": "Find the important details",
    "rag": "Get your assistant ready",
}


def render_steps(placeholder):
    """Refresh the same sidebar slot as each processing stage changes."""
    with placeholder.container():
        for key, label in STEPS.items():
            state = st.session_state.pipeline_steps.get(key, "pending")
            icon = {"done": "check_circle", "active": "progress_activity", "error": "error"}.get(state, "radio_button_unchecked")
            st.caption(f":material/{icon}: {label}")


with st.sidebar:
    st.title("GetNote")
    st.caption("A little clarity for every word.")
    st.space("small")
    st.badge("Your workspace", icon=":material/auto_awesome:", color="green")
    st.subheader("Start with a video")
    st.caption("Start with a meeting, a lecture, or a YouTube or Loom video.")
    with st.form("recording_form", border=False):
        source = st.text_input(
            "YouTube / Loom link or local file path", placeholder="Paste a link or file path…",
            help="Use a public YouTube or Loom video link. For a local file, enter its full path on the computer running this app.",
            key="recording_source",
        )
        uploaded_file = st.file_uploader(
            "Or upload audio or video", type=MEDIA_EXTENSIONS,
            help="Choose one file, leaving the link/path field empty. Processing files are temporary.",
            key="recording_upload",
        )
        language = st.selectbox(
            "Spoken language", ["english", "hinglish"],
            format_func=lambda value: {"english": "English", "hinglish": "Hinglish → English"}[value],
            help="Hinglish videos are translated into English using Sarvam AI.",
        )
        run_btn = st.form_submit_button(
            "Create my notes", icon=":material/auto_awesome:", type="primary", width="stretch"
        )
    st.caption("Longer videos may take a few minutes.")
    sidebar_progress = st.empty()
    if st.session_state.pipeline_steps:
        render_steps(sidebar_progress)
    with st.expander("What can I start with?", icon=":material/help_outline:"):
        st.markdown(
            "- **YouTube:** paste the video's full URL.\n"
            "- **Loom:** paste a public video's share or embed link. Protected videos aren't supported.\n"
            "- **Audio or video:** upload a file, or paste its full local file path.\n"
            "- **English or Hinglish:** choose the language spoken in the video."
        )

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.caption("YOUR MEETING COMPANION")
    if st.session_state.result:
        st.badge("Notes ready", icon=":material/check_circle:", color="green")
    else:
        st.badge("Make room for the good ideas", icon=":material/lightbulb:", color="orange")
st.title("Big conversations. Clear takeaways.")
st.markdown("Turn your videos into useful notes, clear next steps, and answers you can come back to.")
st.space("small")

if run_btn:
    if uploaded_file is not None and source.strip():
        st.warning("Choose one source: remove the uploaded file or clear the link/path field.", icon=":material/info:")
    elif uploaded_file is None and not source.strip():
        st.warning("Upload a file or add a YouTube / Loom link or local file path in the sidebar to get started.", icon=":material/link:")
    elif uploaded_file is not None and uploaded_file.size == 0:
        st.warning("The uploaded file is empty. Choose another file.", icon=":material/info:")
    else:
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_done = False
        st.session_state.pipeline_steps = {}
        st.session_state.pop("chat_playback", None)
        with st.status("Making sense of your video…", expanded=True) as status:
            try:
                # Keep the welcome screen light: load model integrations on submission.
                from utils.audio_processor import process_input
                from core.transcriber import transcribe_all
                from core.analysis import analyze_meeting
                from core.rag_engine import build_rag_chain

                def update_step(key, state):
                    st.session_state.pipeline_steps[key] = state
                    render_steps(sidebar_progress)

                update_step("audio", "active")
                st.write("Preparing your audio.")
                with media_source(source.strip(), uploaded_file) as processing_source:
                    chunks = process_input(processing_source)
                    update_step("audio", "done")
                    update_step("transcript", "active")
                    st.write("Listening and writing your transcript.")
                    timed_transcript = transcribe_all(chunks, language, with_timestamps=True)
                    transcript = timed_transcript.text
                update_step("transcript", "done")
                update_step("analysis", "active")
                analysis_progress = st.empty()

                def show_analysis_progress(stage, completed, total):
                    label = "Reading transcript sections" if stage == "chunks" else "Bringing your notes together"
                    analysis_progress.caption(f"{label} · {completed} of {total}")

                analysis = analyze_meeting(transcript, on_progress=show_analysis_progress)
                update_step("analysis", "done")
                update_step("rag", "active")
                st.write("Getting ready for your questions.")
                rag_chain = build_rag_chain(timed_transcript, source_url=source.strip())
                update_step("rag", "done")
                playback = None
                if uploaded_file is not None:
                    # Keep the original upload for cited playback after temporary
                    # processing files are removed. Never include it in exports.
                    playback = {"data": uploaded_file.getvalue(), "name": uploaded_file.name}
                elif not source.strip().startswith(("http://", "https://")):
                    playback = {"path": source.strip(), "name": Path(source.strip()).name}
                st.session_state.result = {
                    **analysis, "transcript": transcript, "rag_chain": rag_chain,
                    "transcript_segments": timed_transcript.segments, "playback": playback,
                }
                st.session_state.pipeline_done = True
                status.update(label="Your notes are ready. Let's take a look!", state="complete", expanded=False)
            except Exception as exc:
                for key, state in st.session_state.pipeline_steps.items():
                    if state == "active":
                        st.session_state.pipeline_steps[key] = "error"
                render_steps(sidebar_progress)
                status.update(label="We couldn't finish this video", state="error", expanded=True)
                st.error(str(exc))
                st.caption("Check your media source and provider settings, then try again.")
        if st.session_state.pipeline_done:
            st.rerun()

if st.session_state.result:
    result = st.session_state.result
    st.subheader(result["title"])
    st.caption("Your conversation, with the important parts brought into focus.")
    notes_col, chat_col = st.columns([1.65, 1], gap="large")
    with notes_col:
        overview, transcript_tab, downloads_tab = st.tabs(["Meeting notes", "Full transcript", "Save & share"])
        with overview:
            with st.container(border=True):
                st.subheader("The big picture", icon=":material/subject:")
                st.markdown(result["summary"])
            for title, icon, key in [
                ("What happens next", "task_alt", "action_items"),
                ("Decisions made", "verified", "key_decisions"),
                ("Still to explore", "help_outline", "open_questions"),
            ]:
                with st.container(border=True):
                    st.subheader(title, icon=f":material/{icon}:")
                    st.markdown(result[key])
        with transcript_tab:
            st.caption("The full conversation, ready whenever you need the details.")
            with st.container(height=480, border=True):
                st.text(result["transcript"])
        with downloads_tab:
            st.subheader("Take your notes with you", icon=":material/download:")
            st.caption("Save a report, share the takeaways, or keep the complete bundle.")
            downloads = build_downloads(result, st.session_state.chat_history)
            filename = export_filename(result["title"])
            with st.container(border=True):
                st.markdown("**Your complete report**")
                st.caption("Includes your notes, transcript, and current conversation.")
                for label, artifact, mime in [
                    ("Markdown report", "report.md", "text/markdown; charset=utf-8"),
                    ("Plain text report", "report.txt", "text/plain; charset=utf-8"),
                    ("Everything in a ZIP", "all_results.zip", "application/zip"),
                ]:
                    st.download_button(
                        label, data=downloads[artifact], file_name=f"{filename}_{artifact}",
                        mime=mime, on_click="ignore", icon=":material/download:", width="stretch",
                    )
                st.caption("The ZIP also includes individual text files and structured JSON.")
            with st.expander("Just one section?", icon=":material/article:"):
                section_labels = dict(RESULT_SECTIONS)
                if st.session_state.chat_history:
                    section_labels["chat"] = "Meeting chat"
                selected = st.selectbox(
                    "Choose a section", list(section_labels), format_func=section_labels.get, key="download_section",
                )
                st.download_button(
                    "Download section", data=downloads[f"{selected}.txt"],
                    file_name=f"{filename}_{selected}.txt", mime="text/plain; charset=utf-8",
                    on_click="ignore", icon=":material/download:",
                )
    with chat_col:
        with st.container(border=True):
            st.subheader("Let's talk about it", icon=":material/chat_bubble_outline:")
            st.caption("Ask a question. Your assistant will look in the transcript for the answer.")
            prompt = None
            with st.container(height=370, border=False):
                if st.session_state.chat_history:
                    for message_index, message in enumerate(st.session_state.chat_history):
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                            render_chat_sources(message, message_index, result.get("playback"))
                else:
                    st.space("small")
                    st.markdown("**A good question goes a long way.**")
                    st.markdown("Need a quick recap or looking for a specific detail? Start here.")
                    for index, question in enumerate([
                        "What were the main takeaways?", "What tasks need following up?",
                        "Which questions are still unanswered?",
                    ]):
                        if st.button(question, key=f"suggestion_{index}", width="stretch"):
                            prompt = question
            render_chat_playback(result.get("playback"))
            typed_prompt = st.chat_input("Ask about your video…", key="meeting_question")
            prompt = typed_prompt or prompt
            if prompt and prompt.strip():
                try:
                    from core.rag_engine import ask_question_with_sources

                    with st.spinner("Looking through your transcript…"):
                        response = ask_question_with_sources(result["rag_chain"], prompt.strip(), st.session_state.chat_history)
                    st.session_state.chat_history.extend([
                        {"role": "user", "content": prompt.strip()},
                        {"role": "assistant", "content": response["answer"],
                         "citations": response["citations"], "citation_notice": response.get("citation_notice", "")},
                    ])
                    st.rerun()
                except Exception as exc:
                    st.error(f"Couldn't get an answer: {exc}")
                    st.caption("Try your question again in a moment.")
            if st.session_state.chat_history:
                if st.button("Clear conversation", icon=":material/restart_alt:", type="tertiary"):
                    st.session_state.chat_history = []
                    st.session_state.pop("chat_playback", None)
                    st.rerun()
        st.caption("Answers are based on the transcript. Double-check important details against the video.")
else:
    welcome_col, illustration_col = st.columns([1.15, 1], gap="large", vertical_alignment="center")
    with welcome_col:
        st.badge("From video to clarity", color="green", icon=":material/auto_awesome:")
        st.header("Be there for the conversation.")
        with st.container(border=True):
            st.markdown("**Your first set of notes is three little steps away.**")
            st.markdown(
                "1. **Add your video** — upload a file or paste a link or local file path in the sidebar.\n"
                "2. **Choose the language** — English or Hinglish.\n"
                "3. **Make it useful** — create your notes, then ask away."
            )
    with illustration_col:
        st.image(str(Path(__file__).parent / "assets" / "welcome.svg"), width="stretch", alt="A video becomes clear notes and completed tasks.")
    st.space("small")
    for column, icon, title, description in zip(
        st.columns(3, gap="medium"), ["description", "task_alt", "forum"],
        ["Catch the important parts", "Leave with a next step", "Find your answers"],
        ["A thoughtful summary and a full transcript, without another replay.",
         "Action items, decisions, and open questions in one place.",
         "Have a conversation with your video. Follow your curiosity."],
    ):
        with column.container(border=True):
            st.markdown(f":material/{icon}:")
            st.markdown(f"**{title}**")
            st.caption(description)

st.space("small")
st.caption("Made for meetings, lectures, and those 'what did they say?' moments.")
