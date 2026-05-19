"""High-level :class:`VidPickr` client and the low-level
:class:`VidPickrClient` that wraps the raw HTTP calls.

Most callers only need :class:`VidPickr`. The lower-level client is
exposed for users building custom pipelines (e.g. pumping audio bytes
directly into Whisper without writing a temp file).
"""

from __future__ import annotations

import concurrent.futures
import os
import tempfile
from typing import Optional

import requests

from . import _ffmpeg
from .exceptions import APIError, NoFormatError
from .types import (
    AudioFormat,
    DownloadProgress,
    ProgressCallback,
    Quality,
    Resolution,
    VideoFormat,
    VideoInfo,
)

DEFAULT_BASE_URL = "https://api.vidpickr.com/v1"
_API_KEY_HEADER = "X-API-Key"
_CHUNK_SIZE = 1 << 20  # 1 MiB write blocks


class VidPickrClient:
    """Low-level HTTP client. Three methods: :meth:`info`,
    :meth:`split_token`, :meth:`stream_to_file`."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
        timeout: float = 90.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({_API_KEY_HEADER: api_key})

    # ─────────────────────────────────────────────────────────────────

    def info(self, url: str) -> VideoInfo:
        """Resolve a YouTube URL into the full format list."""
        resp = self._session.get(
            f"{self.base_url}/info",
            params={"url": url},
            timeout=self.timeout,
        )
        return self._json_or_raise(resp)

    def split_token(self, merge_token: str) -> dict:
        """Exchange a merge token (bundled video+audio) for separate
        video-only and audio-only tokens.

        Returns ``{"video_token": "...", "audio_token": "..."}``.
        """
        resp = self._session.get(
            f"{self.base_url}/split_token",
            params={"token": merge_token},
            timeout=self.timeout,
        )
        return self._json_or_raise(resp)

    def stream_to_file(self, token: str, out_path: str) -> int:
        """Stream a single track to a file. Returns total bytes written."""
        with self._session.get(
            f"{self.base_url}/stream",
            params={"token": token},
            stream=True,
            timeout=self.timeout,
        ) as resp:
            if not resp.ok:
                raise self._build_api_error(resp)
            written = 0
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=_CHUNK_SIZE):
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
            return written

    def subtitle(self, token: str, fmt: str = "srt") -> str:
        """Fetch a caption track in the requested format. Returns the
        track as a string."""
        resp = self._session.get(
            f"{self.base_url}/subtitle",
            params={"token": token, "format": fmt},
            timeout=self.timeout,
        )
        if not resp.ok:
            raise self._build_api_error(resp)
        return resp.text

    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _json_or_raise(resp: requests.Response) -> dict:
        if not resp.ok:
            raise VidPickrClient._build_api_error(resp)
        return resp.json()

    @staticmethod
    def _build_api_error(resp: requests.Response) -> APIError:
        code = f"http_{resp.status_code}"
        message = f"HTTP {resp.status_code} {resp.reason}"
        try:
            body = resp.json()
            err = body.get("error") if isinstance(body, dict) else None
            if isinstance(err, dict):
                code = err.get("code", code)
                message = err.get("message", message)
        except ValueError:
            # Body wasn't JSON — keep the HTTP defaults.
            pass
        retry = resp.headers.get("Retry-After")
        retry_after = int(retry) if retry and retry.isdigit() else None
        return APIError(code, message, resp.status_code, retry_after)


class VidPickr:
    """High-level SDK. One construction, one ``download()`` per video."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._client = VidPickrClient(api_key, base_url=base_url, session=session)

    @property
    def raw(self) -> VidPickrClient:
        """Access the low-level HTTP client for custom pipelines."""
        return self._client

    def info(self, url: str) -> VideoInfo:
        """Resolve only — return the format list without downloading."""
        return self._client.info(url)

    def download(
        self,
        url: str,
        *,
        out: str,
        quality: Quality = "best",
        video_codec: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> str:
        """Resolve + stream + mux + write. Returns the output path on
        success.

        Steps:
          1. ``/v1/info`` to list formats
          2. Pick the best video + audio for the requested quality
          3. ``/v1/split_token`` to separate the merge token (video formats only)
          4. Stream both tracks in parallel into temp files
          5. ffmpeg ``-c copy`` mux into ``out``
          6. Delete temps

        Raises:
          :class:`APIError` on /info / /split_token / /stream failures
          :class:`NoFormatError` when ``quality`` doesn't match anything
          :class:`FFmpegMissingError` when ffmpeg isn't available
        """
        _tick(on_progress, phase="resolving")

        info = self._client.info(url)

        if not info.get("resolutions"):
            raise NoFormatError(f"No video formats returned for {url}")

        video = _pick_video(info, quality=quality, codec=video_codec)
        audio = _pick_audio(info)

        merge_token = video["download_token"]
        split = self._client.split_token(merge_token)
        v_token = split["video_token"]
        a_token = audio["download_token"]

        with tempfile.TemporaryDirectory(prefix="vidpickr-") as tmp:
            v_path = os.path.join(tmp, "video.mp4")
            a_path = os.path.join(tmp, "audio.m4a")

            _tick(on_progress, phase="fetching")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                v_future = ex.submit(self._client.stream_to_file, v_token, v_path)
                a_future = ex.submit(self._client.stream_to_file, a_token, a_path)
                v_bytes = v_future.result()
                a_bytes = a_future.result()

            _tick(on_progress, phase="muxing", video_bytes=v_bytes, audio_bytes=a_bytes)
            _ffmpeg.mux_stream_copy(v_path, a_path, out)

        _tick(on_progress, phase="done")
        return out


# ─────────────────────────────────────────────────────────────────────


def _pick_video(
    info: VideoInfo,
    *,
    quality: Quality,
    codec: Optional[str],
) -> Resolution:
    resolutions = sorted(info.get("resolutions", []), key=lambda r: -r["height"])
    if not resolutions:
        raise NoFormatError("No video formats available")

    if quality == "lowest":
        target = resolutions[-1]
    elif quality in ("best", "highest"):
        target = resolutions[0]
    elif isinstance(quality, int):
        exact = next((r for r in resolutions if r["height"] == quality), None)
        target = exact or next((r for r in resolutions if r["height"] <= quality), resolutions[-1])
    else:
        raise NoFormatError(f"Unrecognized quality {quality!r}")

    if codec:
        # Resolution entries don't expose multiple codec variants in the
        # current /info shape — codec selection happens server-side.
        # Forward-compat: if a future response carries video_only[], pick
        # the matching codec there.
        variants = target.get("video_only") if isinstance(target, dict) else None  # type: ignore[assignment]
        if variants:
            wanted = _codec_prefix(codec)
            match = next((v for v in variants if v.get("vcodec", "").lower().startswith(wanted)), None)
            if match:
                # Return a synthetic resolution dict pointing at the matched variant.
                return {**target, "download_token": match["download_token"]}

    return target


def _pick_audio(info: VideoInfo) -> AudioFormat:
    formats = info.get("audio_only") or []
    if not formats:
        raise NoFormatError("No audio formats available")
    # Highest bitrate; prefer m4a (AAC) over webm (Opus) when tied because
    # ffmpeg's MP4 stream-copy path likes AAC.
    def _key(f: AudioFormat) -> tuple[int, int]:
        is_m4a = 1 if f.get("ext") == "m4a" else 0
        return (f.get("bitrate", 0), is_m4a)
    return max(formats, key=_key)


def _codec_prefix(kind: str) -> str:
    return {
        "av1": "av01",
        "vp9": "vp9",
        "avc": "avc",
        "hevc": "hev",
    }.get(kind, kind)


def _tick(callback: Optional[ProgressCallback], **kwargs) -> None:
    if callback is None:
        return
    payload: DownloadProgress = {
        "phase": kwargs.pop("phase"),
        "video_bytes": kwargs.pop("video_bytes", 0),
        "audio_bytes": kwargs.pop("audio_bytes", 0),
        "video_total": 0,
        "audio_total": 0,
    }
    callback(payload)
