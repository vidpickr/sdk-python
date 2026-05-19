"""Typed exception classes so callers can branch on error.code or class."""

from __future__ import annotations

from typing import Optional


class APIError(Exception):
    """Raised when the VidPickr API returns a 4xx/5xx response.

    Mirrors the {"error": {"code", "message"}} JSON shape. Branch on
    ``code`` (stable identifier) rather than ``message`` (human text,
    may change between API versions).
    """

    def __init__(self, code: str, message: str, status: int, retry_after: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after = retry_after

    def __repr__(self) -> str:
        return f"APIError(code={self.code!r}, status={self.status}, message={str(self)!r})"


class FFmpegMissingError(Exception):
    """Raised when the muxer can't find an ffmpeg binary on PATH and the
    optional ``[bundled-ffmpeg]`` extra isn't installed either.

    Tells the user exactly how to fix it.
    """

    def __init__(self) -> None:
        super().__init__(
            "ffmpeg is required to mux video + audio tracks. Install it system-wide "
            "(brew install ffmpeg / apt install ffmpeg / winget install ffmpeg) "
            "or reinstall vidpickr with the bundled extra: "
            "pip install 'vidpickr[bundled-ffmpeg]'"
        )


class NoFormatError(Exception):
    """Raised when the requested quality / codec combination doesn't exist
    in the /info response (e.g. requested 4K on a 720p-max video)."""
