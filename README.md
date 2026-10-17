# AI Video Assistant

AI Video Assistant turns meeting recordings, YouTube videos, and public Loom videos into searchable meeting intelligence. It extracts the audio, creates a transcript, generates a professional summary, identifies action items, decisions, and unresolved questions, and provides a conversational RAG chatbot grounded in the meeting transcript. The application supports follow-up questions.

## Features

- YouTube and public Loom links, local audio/video paths, and browser file uploads
- Consistent mono 16 kHz, 16-bit PCM WAV for every input
- Ten-minute audio chunking for reliable transcription
- English transcription with local OpenAI Whisper
- Hinglish transcription and English translation with Sarvam AI
- Automatic meeting title generation
- Shared chunk analysis for summaries, tasks, decisions, and questions
- Action-item extraction with owner and deadline when available
- Key-decision extraction
- Open-question and follow-up extraction
- Transcript-grounded RAG chat using Chroma and sentence-transformer embeddings
- Multi-turn conversational RAG with follow-up question rewriting
- Bounded chat history to reduce prompt growth
- Timestamped chatbot citations with source excerpts and YouTube time links
- Cited playback for uploaded/local audio and video; approximate Hinglish passage times
- Streamlit web interface
- Download complete Markdown/text reports, individual results, and a ZIP with JSON and chat exports
- Interactive Python CLI

## Architecture

```text
YouTube/Loom URL, uploaded file, or local media path
              |
              v
       Audio acquisition
       conversion + chunking
              |
              v
          Transcription
       Whisper or Sarvam AI
              |
              v
          Meeting transcript
              |
      +---------------------------+
      |                           |
      v                           v
  Shared chunk analysis       Vector store
  (bounded concurrency)         Chroma +
      |                   HuggingFace embeddings
      v                           |
  Merge chronological notes       v
      |                   Conversational RAG
      v
  Title + summary + tasks + decisions + open questions
```

### RAG request flow

```text
Current question + compact conversation history
                    |
                    v
       Standalone-question rewriting
                    |
                    v
       Retrieve relevant transcript chunks
                    |
                    v
      Revised question + transcript context
                    |
                    v
                 Answer
```

The conversation history is used only to resolve references during question rewriting. The final-answer prompt receives the revised standalone question and retrieved transcript context, which keeps the answer request smaller and transcript-grounded.

## Project Structure

```text
.
|-- app.py                         # Streamlit web application
|-- main.py                        # CLI pipeline and chat entry point
|-- Requirements.txt               # Python dependencies
|-- .env.example                   # Environment variable template
|-- core/
|   |-- analysis.py                # Shared chunk analysis and bounded merges
|   |-- llm.py                     # Configurable provider factory
|   |-- extractor.py               # Extraction compatibility helpers
|   |-- rag_engine.py              # Conversational RAG chain
|   |-- summarizer.py              # Title/summary compatibility helpers
|   |-- transcriber.py             # Whisper and Sarvam routing
|   `-- vector_store.py            # Chroma indexing and retrieval
|-- utils/
|   |-- audio_processor.py         # Download, conversion, and chunking
|   `-- uploads.py                 # Temporary uploaded media and cleanup
`-- docs/
    |-- technical-documentation.md # Current architecture and implementation
    `-- changes/                   # Implementation change notes
```

Read the [implementation change notes](docs/changes/) for short summaries and
details of provider configuration, shared chunk analysis, conversational RAG,
and result downloads.

Read the [technical documentation](docs/technical-documentation.md) for the
current architecture, module behavior, recovery, storage, and known limitations.

## Requirements

- Python 3.10 or newer
- FFmpeg installed and available on `PATH`
- An API key for your selected LLM provider (Mistral, Gemini, Groq, OpenAI, Anthropic, or an OpenAI-compatible service)
- A Sarvam API key only when using Hinglish transcription
- Internet access for YouTube/Loom downloads, API calls, and initial model downloads
- Enough disk space for Whisper, embedding models, downloaded media, and Chroma data

Whisper runs locally, but it requires PyTorch and can use significant CPU, memory, and disk resources. The default Whisper model is `small` and can be changed with `WHISPER_MODEL`.

## Installation

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd AI-Video-Assistant-
```

### 2. Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r Requirements.txt
```

### 4. Install FFmpeg

FFmpeg must be installed separately because `ffmpeg-python` provides Python bindings but does not install the FFmpeg binary.

Verify the installation:

```bash
ffmpeg -version
```

On Windows, install FFmpeg and add its `bin` directory to `PATH`. On macOS, install it with Homebrew. On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install ffmpeg
```

### 5. Configure environment variables

Copy `.env.example` to `.env` and add your keys:

```env
MISTRAL_API_KEY=your_mistral_api_key
LLM_PROVIDER=mistral
LLM_MODEL=mistral-small-latest
SARVAM_API_KEY=your_sarvam_api_key
WHISPER_MODEL=small
```

`SARVAM_API_KEY` is required only for `hinglish` mode. Never commit `.env` or API keys to GitHub.

### Switching LLM providers

All title, summary, extraction, and conversational RAG calls use the shared
factory in `core/llm.py`. Set `LLM_PROVIDER`, `LLM_MODEL`, and the matching key
in `.env`, then restart the app. Choose a model ID available in your provider
account; a valid key does not guarantee access to every model.

- `mistral`: `MISTRAL_API_KEY`
- `gemini`: `GOOGLE_API_KEY` (Gemini Developer API)
- `groq`: `GROQ_API_KEY`
- `openai`: `OPENAI_API_KEY`
- `anthropic`: `ANTHROPIC_API_KEY` (Claude models)
- `openai_compatible`: `LLM_API_KEY` and `LLM_BASE_URL` (the service's API base URL, usually ending in `/v1`)

For example, to select Groq:

```env
LLM_PROVIDER=groq
LLM_MODEL=your_available_groq_model_id
GROQ_API_KEY=your_groq_api_key
```

For Anthropic Claude:

```env
LLM_PROVIDER=anthropic
LLM_MODEL=your_available_claude_model_id
ANTHROPIC_API_KEY=your_anthropic_api_key
```

For another OpenAI-compatible service:

```env
LLM_PROVIDER=openai_compatible
LLM_MODEL=your_service_model_id
LLM_BASE_URL=https://your-service.example/v1
LLM_API_KEY=your_service_api_key
```

Install the updated `Requirements.txt` once to get all supported integrations.
Only the selected integration is imported at runtime. Missing keys or integrations
produce configuration errors; the app never silently switches providers.
Existing `.env` files with only `MISTRAL_API_KEY` continue to use
`mistral-small-latest`. Environment variables already set in your shell take
precedence over `.env`; remove stale shell values when switching configurations.
Speech transcription and local embeddings are configured separately.

## Running the Application

### Streamlit web interface

For the configured Windows workspace, run this from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

This uses the project's `.venv` and adds the project-local FFmpeg in
`.tools/ffmpeg` to the app's process path. Configure your chosen LLM provider
and its real API key in `.env` before analysing a video; `SARVAM_API_KEY` is needed for Hinglish.
Whisper and embedding models download on first use.

For other environments:

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit, usually `http://localhost:8501`.

In the sidebar:

1. Upload an audio/video file, or enter a YouTube/Loom URL or local media-file path. Use one source at a time.
2. Select **English** or **Hinglish → English**.
3. Select **Create my notes**.
4. Review the generated title, summary, transcript, action items, decisions, and open questions.
5. Ask questions in the meeting chat.
6. Open **Save & share** to save a full report, an individual result, or the ZIP bundle. Reports and bundles include the current chat when available.

Uploads support MP4, MOV, MKV, WebM, AVI, M4V, MP3, WAV, M4A, AAC, OGG,
FLAC, and Opus, subject to FFmpeg's decoder support. The uploader uses Streamlit's
configured size limit (200 MB per file by default). Processing starts when you
select **Create my notes**. An uploaded file gets a temporary copy on the app's
computer; that copy, its converted WAV, and audio chunks are removed after
transcription, including on failure. Your original file stays on your computer.
Streamlit keeps the selected upload in session memory until you remove or
replace it, or the session ends.

The Streamlit application stores the current conversation in `st.session_state`. Starting a new analysis or clearing the chat resets the conversation history.

### CLI

```bash
python main.py
```

The CLI asks for a YouTube/Loom URL or local file path and a transcription language. After processing, it starts an interactive chat. Type `exit`, `quit`, or `q` to leave.

## Input Support

### YouTube URL

```text
https://www.youtube.com/watch?v=VIDEO_ID
```

The application downloads the best available audio with `yt-dlp`, converts it directly to mono 16 kHz, 16-bit PCM WAV, and chunks it for transcription. YouTube, Loom, local paths, and uploads all use this same final audio format.

### Loom link

Paste a public Loom video's share or embed link into the same link/path field:

```text
https://www.loom.com/share/VIDEO_ID
https://www.loom.com/embed/VIDEO_ID
```

Loom uses the same audio download, WAV conversion, transcription, analysis,
and chat pipeline as YouTube. No Loom API key is needed. The video must be
accessible without a login or password; private/protected videos and Loom
folder links are not supported. Download failures show the downloader's
details and an access hint. Keep `yt-dlp` current when a site's download
behavior changes. Downloaded WAV files and chunks remain in `downloades/`.

### Local file

Pass a local audio or video path supported by FFmpeg and pydub:

```text
C:\path\to\meeting.mp4
```

The input is converted to mono 16 kHz, 16-bit PCM WAV before chunking.

## Transcription Modes

| Mode | Engine | Behavior | Required key |
| --- | --- | --- | --- |
| `english` | OpenAI Whisper | Local English transcription | None beyond model download |
| `hinglish` | Sarvam AI | Transcribes Hinglish and returns English text | `SARVAM_API_KEY` |

Whisper is loaded lazily on first use. Sarvam requests are split into 25-second pieces because the synchronous Sarvam endpoint accepts audio segments up to 30 seconds.

## Meeting Analysis Pipeline

`main.py` and `app.py` run the following stages:

1. **Audio processing**: download or convert the input and split it into ten-minute WAV chunks.
2. **Transcription**: process every chunk with Whisper or Sarvam.
3. **Shared analysis**: split the transcript into overlapping sections. In one LLM call per section, extract a summary, action items with owners/deadlines, decisions, and questions with any explicit answers. Process at most three sections concurrently by default.
4. **Merge**: combine the chronological notes, deduplicate overlap, reconcile changed decisions, and match questions to answers from later sections. Generate the final title from the combined material. Keep answered questions in intermediate notes; show only unresolved questions in the final report. Long meetings use multiple bounded merge batches.
5. **RAG indexing**: split the original transcript into 500-character chunks with 50-character overlap and store embeddings in Chroma.
6. **Conversational chat**: rewrite follow-up questions, retrieve four relevant chunks, and generate a transcript-grounded answer.

`core/analysis.py` exposes `analyze_meeting(transcript)`, returning the existing
`title`, `summary`, `action_items`, `key_decisions`, and `open_questions` text
fields. The app, CLI, and manual `test.py` runner call it once and share its
result. The old summarizer/extractor functions remain compatibility helpers;
pass the same `analysis=` dictionary to them to avoid repeated analysis.

Normally analysis uses N chunk calls plus one merge call. Larger meetings need
additional merge calls. Each response is strictly decoded as JSON and validated
with Pydantic. Incomplete responses trigger smaller-piece recovery;
truncated output is never accepted as a complete report. This validates
structure, not the factual accuracy of model reasoning.

### Analysis limits

Optional `.env` settings (restart after changes):

```env
ANALYSIS_MAX_CONCURRENCY=3
ANALYSIS_CHUNK_BUDGET=6000
ANALYSIS_OVERLAP_BUDGET=300
ANALYSIS_INPUT_BUDGET=16000
```

Input budgets use a conservative offline estimate of one token per UTF-8 byte,
including the prompts and JSON schema in the full request check. They usually
overestimate native token counts and require no tokenizer download. They are
not exact provider-native counts or a guarantee for every custom model.

Output length uses the selected provider/client's default. The app does not
force an output-token allowance or expose an output-size setting. Provider
defaults and model limits still apply; this does not mean unlimited output.
Length-limit metadata is checked even when JSON is valid, and visibly
incomplete JSON is also rejected.

Recognized provider context-size errors trigger size recovery. If a chunk
hits the provider's output limit, or its request exceeds the input
budget, its source text splits into smaller pieces (at most four recovery split
levels). Merge overflow uses smaller groups (at most
three recovery subdivision levels). If merging still cannot finish or notes
cannot fit the merge budget, the report assembles the validated notes locally,
preserving distinct items and marking the summary **Review needed**. This
fallback removes only exact duplicates, uses an existing title candidate, and
does not claim complete semantic reconciliation. Conflicting explicit answers
are retained and their question remains open. No incomplete JSON is used.

If source chunks never yield valid complete notes after bounded recovery,
analysis still fails explicitly rather than inventing or omitting content.
Authentication, network, and quota errors propagate; clients retain their own
retry behavior. Set concurrency to `1` for stricter free-tier limits. Recovery
can add calls and cost, but recovery recursion is bounded.

## Conversational RAG Details

The RAG chain accepts history through:

```python
answer = ask_question(rag_chain, question, chat_history)
```

Each history entry has this shape:

```python
{"role": "user", "content": "What was decided?"}
{"role": "assistant", "content": "The launch was moved to Friday."}
```

Before rewriting:

- The latest 4 individual messages are kept verbatim.
- Four messages normally represent 2 complete user/assistant exchanges.
- Older messages are summarized into at most 4 short lines.
- The compacted history and current question are sent to Mistral to create a standalone question.

For final answer generation:

- The revised standalone question is used for retrieval and answering.
- Four relevant transcript chunks are provided as context.
- The final prompt does not receive the full chat history.
- If the transcript does not contain the answer, the assistant returns the configured fallback message.

When older messages exist, a turn can require an additional LLM call to create the compact history summary. The normal flow therefore uses question rewriting and answer generation, with summarization added only when needed.

## Timestamped chatbot citations

New analyses preserve Whisper segment times or approximate Sarvam passage ranges.
The chatbot cites retrieved passages beside each answer claim, for example
`[04:12–04:29]`. Expand **Sources** under an answer to inspect its evidence.
YouTube sources link to the original video at that time. Uploaded and local
files offer **Play from…** controls when the browser supports their media format.
Loom citations display timestamps and excerpts; Loom jump-to-time playback is
not included. `≈` means an approximate passage/chunk range, not sentence timing.

Only chatbot answers get citations. Summaries, action items, decisions, and
questions still receive plain text and do not gain citations automatically.
Whisper timestamps are model estimates and can be imperfect. Source validation
checks IDs and time ranges; it does not prove the model's claim is supported.
Malformed or invalid citation responses trigger at most one additional model
call before an explicit error; authentication/network errors are not hidden.

Re-analyze old videos to capture timestamps. Plain-text callers remain supported
without fabricated times. Code can opt in using
`transcribe_all(chunks, language, with_timestamps=True)` and pass that result to
`build_rag_chain(timed_transcript, source_url=source)`.
`ask_question_with_sources(chain, question, history)` returns `answer` and
`citations`; the existing `ask_question` still returns a string.

Each new index has an isolated collection. To reload a particular analysis,
save `chain.collection_name` and call `load_rag_chain(collection_name)`.
The no-argument loader still refers to the old legacy collection.
Original uploaded media is retained only in the current session for playback;
processing files are still removed. Chat exports retain cited excerpts and
timestamps, but never include media bytes or local playback paths.

Offline regression checks (no model downloads or API keys):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s checks -p "test_timestamp*.py" -v
```

The tests use synthetic WAVs, local test embeddings, and simulated chat-model
responses. They verify functionality, not real-world transcription or answer quality.

## Storage and Generated Files

The application creates local runtime data such as:

- `vector_db/`: Chroma persistence directory
- `downloades/`: downloaded audio files from YouTube and Loom
- Converted WAV files and audio chunks next to the source media
- Temporary Sarvam audio pieces, which are removed after each request

These files can be large. Review storage and cleanup behavior before processing many videos.

## Limitations and Future Improvements

- New analyses use separate vector-store collections; old legacy collections are not migrated automatically. Persisted collections still need a retention/cleanup policy.
- Audio and generated artifacts need an explicit cleanup policy for long-term use.
- The final answer is grounded in retrieved transcript chunks; retrieval quality depends on chunking and embedding quality.
- The current conversational summary is generated on demand when older turns exceed the recent-message window.
- Authentication, multi-user sessions, deployment configuration, and observability are not included.

---

Built by **Shiwansh Singh**.
