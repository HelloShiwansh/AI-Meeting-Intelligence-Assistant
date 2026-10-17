# Loom video links

## Summary

- Added public Loom share/embed links to the existing link input in Streamlit and the CLI.
- Reused yt-dlp and the existing pipeline; every input now produces mono 16 kHz, 16-bit PCM WAV before chunking, with no Loom API key needed.
- Fixed downloaded-file detection to use the actual WAV path reported after conversion, including when Loom supplies MP4 instead of WebM/M4A.
- Added an access hint for failed downloads and rejected Loom folder links; login/password support is outside this change.
- Updated documentation and the yt-dlp minimum to the tested version, with checks for Loom routing, filename handling, errors, and existing inputs.

## Details

Paste a public `https://www.loom.com/share/<video-id>` or
`https://www.loom.com/embed/<video-id>` URL into the same field used for YouTube
links and local paths, select the spoken language, and create notes. Both
interfaces call `process_input()`, which routes web links to the renamed
`download_video_audio()` helper in `utils/audio_processor.py`.

The downloader selects `bestaudio/best` and uses `FFmpegExtractAudio` to produce
WAV. It now reads yt-dlp's postprocessed `requested_downloads[0].filepath`
(or the top-level filepath when applicable) and verifies that the WAV exists.
Previously, replacing `.webm` and `.m4a` in the original prepared filename
could return an MP4 filename or alter matching text inside a title.

All inputs now produce mono 16 kHz, 16-bit PCM WAV before ten-minute chunking.
For YouTube and Loom, `extractaudio+ffmpeg_o` supplies `-ac 1 -ar 16000 -c:a
pcm_s16le` during the existing FFmpeg extraction, so no second WAV conversion
or copy is needed. Local files and uploads use pydub's `set_channels(1)`,
`set_frame_rate(16000)`, and `set_sample_width(2)`. The unused compressed-audio
quality setting was removed. Storage and upload cleanup behave as before.
Previously generated files are not changed in bulk; rerun processing to
generate normalized output. This changes the audio format, not its volume.

Only individual Loom videos accessible without signing in or supplying a
password are supported. Folder links fail before download. Download errors
include an access hint and the original downloader details, including codec,
network, or FFmpeg failures. The app has no Loom login or password setting.
`Requirements.txt` now requires `yt-dlp>=2026.8.19`, matching the installed
version used for verification. Site changes may still require later updates.

Checks cover MP4/WebM/M4A download metadata, titles containing extension-like
text, missing output files, protected-video errors, share/embed extraction,
source routing, and submission through the Streamlit form. Model and
transcription integrations are mocked in the automated suite.

A live smoke check also downloaded yt-dlp's public 26.7-second Loom example,
opened the converted WAV, and created a transcription-ready chunk. The smoke
check used a temporary directory and removed its test media afterward; it
made no transcription or LLM calls.

Normalization checks read actual WAV headers for downloaded MP4 audio, local
audio/video, uploads, and their chunks: one channel, 16,000 Hz, and two bytes
per sample, with duration preserved. A further live Loom check verified the
same format in the downloaded WAV and chunk. WAV output and chunk file handles
are closed explicitly so upload cleanup can release them on Windows.

## File uploads

- Added a sidebar audio/video uploader. Choose a file, select the language, and click **Create my notes**; use either an upload or a link/path.
- Uploads reuse local-file processing: mono 16 kHz WAV, chunking, transcription, analysis, and chat. The configured Streamlit size limit applies (200 MB by default).
- `utils/uploads.py` saves a temporary copy and removes it, its converted WAV, and chunks after transcription, including on failure. The original file stays untouched; Streamlit retains the selected upload in session memory.
- Empty files and conflicting sources show a message without replacing existing notes. Tests cover submission, language routing, cleanup, and reruns; no new dependencies were needed.
