"""
Generate site/public/og-image.png — the social-share preview card.

Mimics the site's newspaper/paper aesthetic: cream background, dark ink,
serif type, navy accent. Renders the wordmark + tagline + a small footer.
Re-run if the wordmark or tagline changes:

    python3 site/build_og_image.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "public" / "og-image.png"

# Site palette
PAPER = (247, 242, 231)
INK = (28, 24, 19)
INK_MUTED = (110, 99, 85)
ACCENT = (26, 54, 93)
RULE = (205, 195, 173)

W, H = 1200, 630
PAD = 80

GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_B = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
GEORGIA_I = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # Top kicker: "FHSAA · 2026 baseball"
    kicker = ImageFont.truetype(GEORGIA, 26)
    draw.text((PAD, PAD), "FHSAA · 2026 BASEBALL", fill=INK_MUTED, font=kicker)

    # Wordmark: open · bethel
    wm_size = 140
    wm_open = ImageFont.truetype(GEORGIA, wm_size)
    wm_bethel = ImageFont.truetype(GEORGIA_B, wm_size)
    y_wm = PAD + 70
    x = PAD
    draw.text((x, y_wm), "open", fill=INK, font=wm_open)
    open_w = draw.textlength("open", font=wm_open)
    dot_w = draw.textlength(" · ", font=wm_open)
    draw.text((x + open_w, y_wm), " · ", fill=ACCENT, font=wm_open)
    draw.text((x + open_w + dot_w, y_wm), "bethel", fill=INK, font=wm_bethel)

    # Rule line
    rule_y = y_wm + wm_size + 40
    draw.line([(PAD, rule_y), (W - PAD, rule_y)], fill=RULE, width=2)

    # Tagline
    tagline = "An open, auditable ranking engine."
    tagline_font = ImageFont.truetype(GEORGIA_I, 38)
    draw.text((PAD, rule_y + 30), tagline, fill=INK, font=tagline_font)

    sub = "Every ranking explainable down to the individual game."
    sub_font = ImageFont.truetype(GEORGIA, 30)
    draw.text((PAD, rule_y + 90), sub, fill=INK_MUTED, font=sub_font)

    # Footer URL
    url_font = ImageFont.truetype(GEORGIA_B, 28)
    url = "open-bethel.org"
    url_w = draw.textlength(url, font=url_font)
    draw.text((W - PAD - url_w, H - PAD - 30), url, fill=ACCENT, font=url_font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
