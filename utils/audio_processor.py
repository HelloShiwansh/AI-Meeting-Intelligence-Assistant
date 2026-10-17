import yt_dlp
from pydub import AudioSegment
import os
from urllib.parse import urlparse

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR,exist_ok = True)

def download_video_audio(url: str) -> str:
    """Download one accessible online video and return its postprocessed WAV."""
    parsed = urlparse(url)
    if parsed.hostname in {"loom.com", "www.loom.com"} and parsed.path.startswith("/share/folder/"):
        raise ValueError("Use a single Loom video's share or embed link, rather than a folder link.")
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(
            "Could not download the video. Check that the link is available without "
            f"signing in or a password. Downloader details: {exc}"
        ) from exc

    # prepare_filename() describes the original container. The requested
    # download metadata contains the final path after FFmpeg conversion/moving.
    downloaded = ((info or {}).get("requested_downloads") or [info or {}])[0]
    filename = downloaded.get("filepath")
    if not filename or not filename.lower().endswith(".wav") or not os.path.isfile(filename):
        raise RuntimeError("The download did not produce a WAV audio file. Check the link and FFmpeg installation.")
    return filename



def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000) #16khz
    audio.export(output_path, format="wav")
    return output_path



def chunk_audio(wav_path : str , chunk_minutes : int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000 

    chunks = []

    for i, start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path , format = "wav")

        chunks.append(chunk_path)
    
    return chunks

def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected video URL. Downloading audio...")
        wav_path = download_video_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks


