"""One-call download example.

Run with::

    VIDPICKR_API_KEY=vpk_live_... python examples/basic.py [optional URL]
"""

from __future__ import annotations

import os
import sys

from vidpickr import VidPickr


def main() -> None:
    api_key = os.environ.get("VIDPICKR_API_KEY")
    if not api_key:
        print("Set VIDPICKR_API_KEY first", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    vp = VidPickr(api_key=api_key)
    out = vp.download(
        url,
        out="out.mp4",
        quality=1080,
        on_progress=lambda p: print(f"  {p['phase']}"),
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
