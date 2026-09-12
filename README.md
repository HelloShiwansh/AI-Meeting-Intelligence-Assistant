# AI Video Assistant

AI Video Assistant turns meeting recordings and YouTube videos into searchable meeting intelligence. It extracts the audio, creates a transcript, generates a professional summary, identifies action items, decisions, and unresolved questions, and provides a conversational RAG chatbot grounded in the meeting transcript. The application supports follow-up questions. 

## Features

- YouTube URL and local audio/video file support
- Audio conversion to mono 16 kHz WAV
- Ten-minute audio chunking for reliable transcription
- English transcription with local OpenAI Whisper
- Hinglish transcription and English translation with Sarvam AI
- Automatic meeting title generation
- Map-reduce meeting summarization
- Action-item extraction with owner and deadline when available
- Key-decision extraction
- Open-question and follow-up extraction
- Transcript-grounded RAG chat using Chroma and sentence-transformer embeddings
- Multi-turn conversational RAG with follow-up question rewriting
- Bounded chat history to reduce prompt growth
- Streamlit web interface
- Interactive Python CLI

## Architecture

```text
YouTube URL or local media file
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
      +-------+--------+----------------+
      |                |                |
      v                v                v
   Summary       Extraction        Vector store
                                    Chroma +
                              HuggingFace embeddings
                                        |
                                        v
                                Conversational RAG
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
|   |-- extractor.py               # Action items, decisions, questions
|   |-- rag_engine.py              # Conversational RAG chain
|   |-- summarizer.py              # Title and summary generation
|   |-- transcriber.py             # Whisper and Sarvam routing
|   `-- vector_store.py            # Chroma indexing and retrieval
|-- utils/
|   `-- audio_processor.py         # Download, conversion, and chunking
`-- docs/
    `-- changes/                   # Local implementation notes
```

## Requirements

- Python 3.10 or newer
- FFmpeg installed and available on `PATH`
- A Mistral API key
- A Sarvam API key only when using Hinglish transcription
- Internet access for YouTube downloads, API calls, and initial model downloads
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
SARVAM_API_KEY=your_sarvam_api_key
WHISPER_MODEL=small
```

`SARVAM_API_KEY` is required only for `hinglish` mode. Never commit `.env` or API keys to GitHub.

## Running the Application

### Streamlit web interface

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit, usually `http://localhost:8501`.

In the sidebar:

1. Enter a YouTube URL or local media-file path.
2. Select `english` or `hinglish`.
3. Select **Analyse**.
4. Review the generated title, summary, transcript, action items, decisions, and open questions.
5. Ask questions in the meeting chat.

The Streamlit application stores the current conversation in `st.session_state`. Starting a new analysis or clearing the chat resets the conversation history.

### CLI

```bash
python main.py
```

The CLI asks for a YouTube URL or local file path and a transcription language. After processing, it starts an interactive chat. Type `exit`, `quit`, or `q` to leave.

## Input Support

### YouTube URL

```text
https://www.youtube.com/watch?v=VIDEO_ID
```

The application downloads the best available audio with `yt-dlp`, converts it to WAV, and chunks it for transcription.

### Local file

Pass a local audio or video path supported by FFmpeg and pydub:

```text
C:\path\to\meeting.mp4
```

The input is converted to mono 16 kHz WAV before chunking.

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
3. **Title generation**: ask Mistral for a short professional meeting title.
4. **Summarization**: split the transcript into larger sections, summarize each section, and combine the partial summaries.
5. **Extraction**: identify action items, key decisions, and unresolved questions.
6. **RAG indexing**: split the transcript into 500-character chunks with 50-character overlap and store embeddings in Chroma.
7. **Conversational chat**: rewrite follow-up questions, retrieve four relevant chunks, and generate a transcript-grounded answer.

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

## Storage and Generated Files

The application creates local runtime data such as:

- `vector_db/`: Chroma persistence directory
- `downloades/`: downloaded audio files from YouTube
- Converted WAV files and audio chunks next to the source media
- Temporary Sarvam audio pieces, which are removed after each request

These files can be large. Review storage and cleanup behavior before processing many videos.

## Limitations and Future Improvements

- The current vector-store collection name is shared, so production use should isolate collections per meeting.
- Audio and generated artifacts need an explicit cleanup policy for long-term use.
- The final answer is grounded in retrieved transcript chunks; retrieval quality depends on chunking and embedding quality.
- The current conversational summary is generated on demand when older turns exceed the recent-message window.
- Authentication, multi-user sessions, deployment configuration, and observability are not included.

---

Built by **Shiwansh Singh**.
