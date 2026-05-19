"""VidPickr — Python SDK for the VidPickr API.

Quick start
-----------
    from vidpickr import VidPickr

    vp = VidPickr(api_key="vpk_live_...")
    vp.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        out="video.mp4",
        quality=1080,
    )

That single call resolves the URL through /v1/info, exchanges the merge
token via /v1/split_token, streams the video + audio tracks in parallel
from /v1/stream, then muxes them with ffmpeg (-c copy, no re-encoding).
The output lands at the path you specified.

ffmpeg is invoked as a subprocess from PATH. If you don't have ffmpeg
installed system-wide, install the optional extra to bundle it:

    pip install 'vidpickr[bundled-ffmpeg]'

That pulls imageio-ffmpeg, which ships a platform-matched pre-built
ffmpeg binary inside the wheel. The SDK auto-detects it.
"""

from .client import VidPickr, VidPickrClient
from .exceptions import APIError, FFmpegMissingError, NoFormatError
from .types import (
    AudioFormat,
    DownloadProgress,
    Quality,
    Resolution,
    SubtitleTrack,
    VideoFormat,
    VideoInfo,
)

__version__ = "0.1.0"

__all__ = [
    "VidPickr",
    "VidPickrClient",
    "APIError",
    "FFmpegMissingError",
    "NoFormatError",
    "AudioFormat",
    "VideoFormat",
    "Resolution",
    "SubtitleTrack",
    "VideoInfo",
    "DownloadProgress",
    "Quality",
    "__version__",
]
