"""ffmpeg discovery + invocation.

Looks for an ffmpeg binary in this order:
  1. ``VIDPICKR_FFMPEG`` env var (escape hatch for unusual setups)
  2. ``imageio_ffmpeg`` if the user installed ``vidpickr[bundled-ffmpeg]``
  3. ``ffmpeg`` on PATH

If none are found, raises :class:`vidpickr.FFmpegMissingError` with
clear install instructions.

The mux operation itself is just ``ffmpeg -y -i video -i audio -c copy
out.mp4`` — a stream copy, no re-encoding, takes about a second per
minute of source video.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional

from .exceptions import FFmpegMissingError


def find_ffmpeg() -> Optional[str]:
    """Return an absolute path to an ffmpeg binary, or None if missing.

    Cached after the first lookup so repeat downloads don't re-stat.
    """
    if _CACHED["path"] is not None:
        return _CACHED["path"] or None

    env = os.environ.get("VIDPICKR_FFMPEG")
    if env and os.path.isfile(env):
        _CACHED["path"] = env
        return env

    try:
        import imageio_ffmpeg  # type: ignore[import-untyped]
    except ImportError:
        pass
    else:
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path):
            _CACHED["path"] = path
            return path

    which = shutil.which("ffmpeg")
    if which:
        _CACHED["path"] = which
        return which

    # Cache the miss too (empty string acts as a sentinel) so we don't
    # keep re-scanning PATH on every download call in long-running
    # processes.
    _CACHED["path"] = ""
    return None


_CACHED: dict[str, Optional[str]] = {"path": None}


def mux_stream_copy(video_path: str, audio_path: str, out_path: str) -> None:
    """Mux a video file + an audio file into one MP4 with stream copy.

    No re-encoding; the bytes themselves don't change, only the container
    wrapper. Raises :class:`FFmpegMissingError` when ffmpeg isn't
    available, or :class:`subprocess.CalledProcessError` when ffmpeg
    itself fails (corrupt input, unsupported codec combo, etc.).
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise FFmpegMissingError()

    cmd = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c", "copy",
        out_path,
    ]
    # stderr captured to surface useful errors when the call fails; we
    # don't print it on success to keep the SDK quiet by default.
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
