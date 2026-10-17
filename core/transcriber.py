import os
import requests
import wave
from math import isfinite
from core.transcript import TimestampedTranscript, TranscriptSegment
from pydub import AudioSegment

# Sarvam's sync STT-translate API rejects audio longer than 30s.
# We slice each chunk into 25s pieces (with a 5s safety margin) before sending.
SARVAM_PIECE_SECONDS = 25


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")


SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")

_model = None


def load_model():

    global _model  

    if _model is None: 
        print(f"Loading Whisper model: {WHISPER_MODEL} ...")
        import whisper

        _model = whisper.load_model(WHISPER_MODEL) 
        print("Whisper model loaded.")
    return _model 


def audio_duration(chunk_path: str) -> float:
    """Read the actual WAV duration, including short final chunks."""
    with wave.open(str(chunk_path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def transcribe_chunk_whisper(chunk_path: str, *, with_timestamps: bool = False):
    result = load_model().transcribe(chunk_path, task="transcribe")
    if not with_timestamps:
        return result["text"]
    duration = audio_duration(chunk_path)
    segments = []
    for item in result.get("segments", []):
        text = item["text"].strip()
        raw_start, raw_end = float(item["start"]), float(item["end"])
        if not isfinite(raw_start) or not isfinite(raw_end):
            raise ValueError("Whisper returned an invalid timestamp.")
        start = max(0.0, raw_start)
        end = min(duration, raw_end)
        if text and end > start:
            segments.append(TranscriptSegment(text, start, end))
    # A text-only engine response can still be located within its audio chunk,
    # but must never masquerade as sentence-level timing.
    if not segments and result["text"].strip() and duration > 0:
        segments.append(TranscriptSegment(result["text"].strip(), 0.0, duration, "chunk"))
    return TimestampedTranscript(tuple(segments))


def _send_to_sarvam(piece_path: str) -> str:
    """Send one ≤30s WAV file to Sarvam and return the English transcript."""
    headers = {"api-subscription-key": SARVAM_API_KEY}

    with open(piece_path, "rb") as f:
        files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
        data = {"model": SARVAM_MODEL, "with_diarization": "false"}
        response = requests.post(
            SARVAM_STT_TRANSLATE_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        print(f"\n❌ Sarvam returned {response.status_code}")
        print(f"Response body: {response.text}\n")
        response.raise_for_status()

    return response.json().get("transcript", "")


def transcribe_chunk_sarvam(chunk_path: str, *, with_timestamps: bool = False):
    """
    Sarvam sync API only accepts ≤30s audio. We split this chunk into
    25-second pieces, send each separately, and join the transcripts.
    """
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    with open(chunk_path, "rb") as source:
        audio = AudioSegment.from_wav(source)
    piece_ms = SARVAM_PIECE_SECONDS * 1000

    full_text = ""
    segments = []
    total_pieces = (len(audio) + piece_ms - 1) // piece_ms

    for i, start in enumerate(range(0, len(audio), piece_ms)):
        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        with piece.export(piece_path, format="wav"):
            pass

        try:
            print(f"  Sarvam piece {i + 1}/{total_pieces} ...")
            text = _send_to_sarvam(piece_path).strip()
            full_text += text + " "
            if text:
                segments.append(TranscriptSegment(
                    text, start / 1000, min(start + piece_ms, len(audio)) / 1000,
                    "passage",
                ))
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

    return TimestampedTranscript(tuple(segments)) if with_timestamps else full_text.strip()

   



def transcribe_chunk(chunk_path: str, language: str = "english", *, with_timestamps: bool = False):
    engine = transcribe_chunk_sarvam if language.lower() == "hinglish" else transcribe_chunk_whisper
    return engine(chunk_path, with_timestamps=with_timestamps)


def transcribe_all(chunks: list, language: str = "english", *, with_timestamps: bool = False):
    """Keep legacy text callers working; opt in to original-media timestamps."""
    texts, segments = [], []
    offset = 0.0
    for i, chunk in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")
        result = transcribe_chunk(chunk, language, with_timestamps=with_timestamps)
        if with_timestamps:
            for segment in result.segments:
                segments.append(TranscriptSegment(
                    segment.text, offset + segment.start_seconds,
                    offset + segment.end_seconds, segment.timing_precision,
                ))
            # Include silent chunks in offsets; never infer time from text length.
            offset += audio_duration(chunk)
        else:
            texts.append(result)
    print("Transcription complete.")
    return TimestampedTranscript(tuple(segments)) if with_timestamps else " ".join(texts).strip()
