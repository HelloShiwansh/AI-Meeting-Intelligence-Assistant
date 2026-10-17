"""Temporary media files for the web application's upload control."""

from contextlib import contextmanager
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory


MEDIA_EXTENSIONS = [
    "mp4", "mov", "mkv", "webm", "avi", "m4v",
    "mp3", "wav", "m4a", "aac", "ogg", "flac", "opus",
]


@contextmanager
def media_source(source: str, upload=None):
    """Yield the original source or an isolated, temporary uploaded-media path."""
    if upload is None:
        yield source
        return

    suffix = Path(upload.name).suffix.lower()
    if suffix.lstrip(".") not in MEDIA_EXTENSIONS:
        raise ValueError("Choose a supported audio or video file.")

    with TemporaryDirectory(prefix="getnote-upload-") as directory:
        # Use our own basename so client filenames cannot select server paths.
        path = Path(directory) / f"recording{suffix}"
        upload.seek(0)
        with path.open("wb") as destination:
            copyfileobj(upload, destination)
        if path.stat().st_size == 0:
            raise ValueError("The uploaded file is empty. Choose another file.")
        # Audio conversion and chunking write beside this path, so they are
        # removed with the upload when transcription finishes or raises.
        yield str(path)
