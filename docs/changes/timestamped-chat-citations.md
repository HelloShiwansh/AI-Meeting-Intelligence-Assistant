# Timestamped chatbot citations

## Summary

- Added timestamp ranges beside chatbot answer claims and expandable source excerpts.
- YouTube citations open the original video at the cited start time. Uploaded/local files offer in-app playback from that time when the browser supports the media format.
- Preserved Whisper segment timing and marked Sarvam's approximate passage ranges with `≈`.
- Isolated each new video's vector collection to prevent citations from mixing different videos.
- Summaries, action items, decisions, and open-question extraction still use plain transcript text; citations apply only to chat.

## Details

### Transcription and indexing

- `core/transcript.py` defines timestamped transcript and segment records, validating finite, ordered time ranges.
- `core/transcriber.py` supports `with_timestamps=True`. Whisper retains segment start/end times. Sarvam retains the known boundaries of each 25-second audio piece, including a shorter final piece; those ranges are approximate, not sentence alignment.
- Full-video times add the actual durations of preceding WAV chunks, including silent chunks. Text-only Whisper responses fall back to an explicitly approximate whole-chunk range.
- Existing transcription callers still receive a string by default. The app and CLI request timestamped results and pass their `.text` to shared analysis.
- `core/vector_store.py` maps overlapping retrieval chunks back to their speech segments and stores time ranges, precision, source URL, and video ID in metadata. Each new analysis uses its own collection.

### Answer generation and validation

- `core/rag_engine.py` labels retrieved passages with IDs such as `S1` and asks the model for structured claims and their supporting source IDs.
- `core/citations.py` validates the response and constructs displayed timestamps and YouTube links from retrieved metadata. Unknown source IDs, malformed responses, and empty cited answers are rejected.
- Invalid citation responses get one additional model attempt before an explicit error. Provider/network failures are not hidden by this validation retry.
- Unanswerable questions return the existing fallback without citations. Legacy text-only indexes remain usable without fabricated timestamps; the web chat explains that a new analysis is needed to enable timing.
- Source validation establishes which retrieved passage was cited. It does not independently prove that the passage supports the model's claim.

### Chat UI and playback

- `ask_question_with_sources()` returns an answer plus citation metadata; `ask_question()` retains its string-returning interface.
- `utils/chat_citations.py` renders **Sources** beneath an answer, showing the time range and retrieved excerpt. YouTube sources include a time link.
- For uploaded/local files, **Play from…** selects a start time. A **Source playback** section appears below chat history and above the question input, using native Streamlit audio/video players.
- Uploaded media bytes are retained in the analysis result for playback after temporary processing files are removed. Local media uses its original file path. Playback starts at the cited range's beginning and does not automatically stop at its end.
- Clearing the chat clears the selected playback position. Starting another valid analysis clears the previous result and retained playback reference.
- `utils/exports.py` preserves citation excerpts, timestamps, and YouTube links in chat reports and structured JSON. Media bytes and local playback paths are excluded.
