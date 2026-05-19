# vidpickr

Official Python SDK for the [VidPickr API](https://vidpickr.com/docs). Download YouTube videos with a single function call.

```python
from vidpickr import VidPickr

vp = VidPickr(api_key="vpk_live_...")
vp.download(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    out="video.mp4",
    quality=1080,
)
```

That's it. The SDK:

1. Resolves the URL through `/api/v1/info`
2. Picks the best 1080p video track and the highest-bitrate audio track
3. Exchanges the merge token via `/api/v1/split_token`
4. Streams both tracks in parallel from `/api/v1/stream`
5. Muxes them into one MP4 with `ffmpeg -c copy` (no re-encoding)
6. Writes the result to `video.mp4` and cleans up temp files

## Requirements

- **Python 3.9+**
- A **VidPickr Plus subscription** ($1/mo) and an **API key**, minted at [vidpickr.com/account/api-keys](https://vidpickr.com/account/api-keys)
- **ffmpeg** on PATH — or use the bundled-ffmpeg extra below

## Install

```sh
pip install vidpickr
```

If you don't have ffmpeg installed system-wide and don't want to:

```sh
pip install 'vidpickr[bundled-ffmpeg]'
```

That pulls `imageio-ffmpeg`, which ships a pre-built ffmpeg binary inside the wheel (~50 MB extra disk).

## API

### `VidPickr(api_key, *, base_url=None, session=None)`

Construct the client. `session` accepts a `requests.Session` if you want to share connection pooling or pin a User-Agent.

### `vp.download(url, *, out, quality='best', video_codec=None, on_progress=None) -> str`

Resolve, stream, mux, and write to disk. Returns the output path.

| Argument       | Type                                        | Default | Description                                                          |
|----------------|---------------------------------------------|---------|----------------------------------------------------------------------|
| `out`          | `str`                                       | —       | Output MP4 path. Parent directory must exist.                        |
| `quality`      | `'best' \| 'highest' \| 'lowest' \| int`    | `'best'`| Target height (e.g. `1080`) or preset.                              |
| `video_codec`  | `'av1' \| 'vp9' \| 'avc' \| 'hevc' \| None` | `None`  | Preferred codec when multiple are available at the same height.     |
| `on_progress`  | `Callable[[dict], None] \| None`            | `None`  | Called between phases with `{"phase": ..., "video_bytes": ..., ...}`. |

### `vp.info(url) -> dict`

Resolve only. Returns the `VideoInfo` JSON. Use when you want to inspect formats before deciding.

### `vp.raw`

Access the low-level `VidPickrClient` for custom pipelines (e.g. piping audio bytes into Whisper without writing to disk).

## Errors

```python
from vidpickr import APIError, FFmpegMissingError, NoFormatError

try:
    vp.download(url, out="x.mp4")
except APIError as e:
    if e.code == "rate_limited":
        print(f"Retry in {e.retry_after}s")
    elif e.code == "plus_required":
        print("Subscribe to Plus first.")
    else:
        raise
except FFmpegMissingError as e:
    print(e)  # tells you exactly how to install ffmpeg
except NoFormatError as e:
    print(f"Requested format unavailable: {e}")
```

## Subtitles

```python
info = vp.info(url)
en_track = next(s for s in info["subtitles"] if s["code"] == "en" and not s["is_auto"])
srt = vp.raw.subtitle(en_track["download_token"], fmt="srt")
with open("captions.srt", "w", encoding="utf-8") as f:
    f.write(srt)
```

## Why no Rust extension yet?

The `0.1.0` release uses ffmpeg as a subprocess — fastest path to a working SDK. A future release will ship a tiny Rust extension via PyO3 for in-process MP4 muxing, dropping the ffmpeg dependency entirely (target install footprint ~500 KB instead of 50 MB).

## License

MIT
