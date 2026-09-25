"""Generates a synthetic test image so the vision pipeline can be demoed
without the user having to supply a photo.

The image is a simple flat-colour illustration, clearly labelled as synthetic.
It exercises the code path (image -> Gemini -> report) but its content is
schematic rather than photographic.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw


def sample_obstacle_photo(width: int = 960, height: int = 640) -> bytes:
    """Return PNG bytes for a synthetic 'construction narrowing a walkway' scene."""
    img = Image.new("RGB", (width, height), "#B9C4C2")
    draw = ImageDraw.Draw(img)

    # --- ground: two paving tones split by a kerb line ---------------------
    draw.rectangle([0, int(height * 0.34), width, height], fill="#9AA5A3")
    draw.rectangle([0, int(height * 0.34), int(width * 0.16), height], fill="#7E8B89")
    draw.line([(int(width * 0.16), int(height * 0.34)), (int(width * 0.16), height)],
              fill="#6C7877", width=7)

    # paving joints
    for i in range(1, 9):
        y = int(height * 0.34) + i * int(height * 0.07)
        draw.line([(0, y), (width, y)], fill="#8E9997", width=2)

    # --- hoarding across the right-hand side ------------------------------
    hx0, hx1 = int(width * 0.58), int(width * 0.94)
    hy0, hy1 = int(height * 0.30), int(height * 0.72)
    draw.rectangle([hx0, hy0, hx1, hy1], fill="#E8801A")
    draw.rectangle([hx0, hy0, hx1, hy0 + 12], fill="#C4650D")
    draw.rectangle([hx0, hy1 - 12, hx1, hy1], fill="#C4650D")
    for x in range(hx0, hx1, 34):  # mesh panels
        draw.line([(x, hy0 + 12), (x, hy1 - 12)], fill="#B15A0B", width=2)
    draw.rectangle([hx0, hy0 - 34, hx1, hy0], fill="#F5C518")  # sign board
    draw.rectangle([hx0, hy0 - 30, hx1, hy0 - 4], fill="#1A1A1A")

    # --- warning sign on a post -------------------------------------------
    draw.rectangle([int(width * 0.50), int(height * 0.58), int(width * 0.545), height],
                   fill="#6B7776", width=6)
    draw.rectangle([int(width * 0.455), int(height * 0.50), int(width * 0.585), int(height * 0.60)],
                   fill="#F5C518", outline="#1A1A1A", width=3)

    # --- trailing cable across the approach -------------------------------
    cable = [(int(width * 0.16), int(height * 0.90)),
             (int(width * 0.30), int(height * 0.84)),
             (int(width * 0.44), int(height * 0.92)),
             (int(width * 0.58), int(height * 0.86))]
    draw.line(cable, fill="#20201E", width=9, joint="curve")

    # --- arrows showing the measured gap -----------------------------------
    gap_y = int(height * 0.80)
    draw.line([(hx0, gap_y), (int(width * 0.16), gap_y)], fill="#F5C518", width=6)
    draw.polygon([(hx0, gap_y - 14), (hx0, gap_y + 14), (hx0 - 20, gap_y)], fill="#F5C518")
    draw.polygon([(int(width * 0.16), gap_y - 14), (int(width * 0.16), gap_y + 14),
                  (int(width * 0.16) + 20, gap_y)], fill="#F5C518")

    # --- labels -----------------------------------------------------------
    draw.text((18, 12), "SYNTHETIC TEST IMAGE - not a photograph",
              fill="#1A1A1A")
    draw.text((int(width * 0.455), int(height * 0.525)), "!", fill="#1A1A1A")
    draw.text((int(width * 0.62), int(height * 0.40)), "WORKS ACCESS", fill="#1A1A1A")
    draw.text((int(width * 0.60), int(height * 0.78)), "~1.0 m", fill="#1A1A1A")
    draw.text((int(width * 0.02), int(height * 0.06)), "kerb (full drop, no dropped kerb)",
              fill="#1A1A1A")
    draw.text((int(width * 0.20), int(height * 0.93)), "cable at ground level",
              fill="#F5C518")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def sample_mime() -> str:
    return "image/png"
