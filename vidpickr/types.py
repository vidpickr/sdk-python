"""Type definitions for the public surface.

These are TypedDicts so they describe the JSON shapes coming back from
the API without forcing callers to use any specific runtime class. The
SDK returns plain dicts that match these types; mypy / Pyright pick up
the fields automatically when callers annotate their own variables.
"""

from __future__ import annotations

from typing import Callable, Literal, Optional, TypedDict, Union


class VideoFormat(TypedDict, total=False):
    ext: str
    vcodec: str
    size_mb: Optional[float]
    download_token: str
    endpoint: str  # "merge" or "stream" — implementation hint
    bitrate: int


class AudioFormat(TypedDict, total=False):
    ext: str
    acodec: str
    bitrate: int
    size_mb: Optional[float]
    download_token: str
    endpoint: str


class Resolution(TypedDict, total=False):
    height: int
    quality_label: str
    size_mb: Optional[float]
    is_progressive: bool
    download_token: str
    endpoint: str
    filename: str


class SubtitleTrack(TypedDict, total=False):
    code: str
    name: str
    is_auto: bool
    download_token: str
    filename: str


class VideoInfo(TypedDict, total=False):
    title: str
    thumbnail: str
    platform: str
    duration_sec: int
    resolutions: list[Resolution]
    audio_only: list[AudioFormat]
    subtitles: list[SubtitleTrack]


# 'best' / 'highest' → top available height
# 'lowest'           → smallest available
# int                → exact match, fall back to next-lower available
Quality = Union[Literal["best", "highest", "lowest"], int]


class DownloadProgress(TypedDict, total=False):
    phase: Literal["resolving", "fetching", "muxing", "finalizing", "done"]
    video_bytes: int
    audio_bytes: int
    video_total: int
    audio_total: int


ProgressCallback = Callable[[DownloadProgress], None]
