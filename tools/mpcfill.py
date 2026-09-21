#!/usr/bin/env python3
"""Compose print-ready card fronts and write an MPC Autofill order file.

The art in `assets/` is illustration only -- no name, no attributes, no rules
text -- so this script lays the printed card over it and then writes the XML
that MPC Autofill's desktop tool feeds to MakePlayingCards.

    python tools/mpcfill.py                       # both renditions into build/
    python tools/mpcfill.py --profile web         # just the browsable one
    python tools/mpcfill.py --no-agendas          # 84 cards instead of 92
    python tools/mpcfill.py --only 26,41          # re-render two cards while tweaking

What comes out of `build/mpc/`:

    cards/00 Cardback.png          the shared back
    cards/01 Beloved of the Gods.png ... one front per deck slot
    succession.xml                 the order file, with absolute local paths

Then drop the `autofill` executable next to `succession.xml` and run it.

Geometry is MakePlayingCards' standard poker card: 2.72 x 3.70 in with bleed,
trimming to 2.48 x 3.46 in. The desktop tool reads DPI off image height as
300px per 1110px of height, and downscales anything above 800 DPI, so 600 is a
comfortable default -- it keeps the rules text crisp without a 4000px upload.

Needs Pillow (`pip install pillow`); the simulator itself stays stdlib-only.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.dom import minidom

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from succession.cards import CardDef, build_cards  # noqa: E402
from succession.courtiers import COURTIERS_BY_NAME  # noqa: E402
from succession.enums import SEAT_ESTATE, Family, Origin, People, Seat  # noqa: E402
from tools import card_text, cardlist, gallery  # noqa: E402
from tools.assets import AssetMismatch  # noqa: E402
from tools.assets import map_to_deck, scan  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # pragma: no cover - environment guard
    sys.exit(
        "This script needs Pillow to compose the card fronts.\n"
        "    pip install pillow\n"
        "(The simulator in succession/ has no dependencies; this is print "
        "tooling only.)"
    )

# --- Geometry ---------------------------------------------------------------
# MakePlayingCards' standard poker card. The outer 0.12 in on every side is
# bleed that the cutter takes off, and the cut wanders by a millimetre or so,
# so nothing that matters goes within SAFE_IN of the edge.
BLEED_W_IN = 2.72
BLEED_H_IN = 3.70
#: What survives the cutter, and what the web version shows.
TRIM_W_IN = 2.48
TRIM_H_IN = 3.46
BLEED_MARGIN_IN = (BLEED_W_IN - TRIM_W_IN) / 2
SAFE_IN = 0.20

#: The border is drawn from the bleed edge inwards, so the cut lands *inside*
#: it and takes 0.12 in off: 0.22 here prints as a 0.10 in (2.5 mm) border, in
#: the range a Magic card uses. That is the whole point of a thick border -- a
#: millimetre of drift changes its width by a millimetre, which nobody sees,
#: where the same drift against a thin keyline set in from the trim is glaring.
BORDER_IN = 0.22
#: Where the plates start: just inside the border, not at the bleed edge.
CONTENT_IN = BORDER_IN + 0.05

#: The desktop tool reads an image's DPI as `300 * height / 1110`, i.e. it
#: expects exactly the 3.70 in of bleed height we render to, and downscales
#: anything above 800 DPI before upload.
assert abs(1110 / 300 - BLEED_H_IN) < 1e-9, "bleed height disagrees with the desktop tool"
MAX_USEFUL_DPI = 800

# Plate metrics, in inches. Everything else is derived from these.
PLATE_PAD_IN = 0.075
PLATE_RADIUS_IN = 0.055
NAME_SIZE_IN = 0.122
NAME_MIN_SIZE_IN = 0.082
TYPE_SIZE_IN = 0.060
BODY_SIZE_IN = 0.086
BODY_MIN_SIZE_IN = 0.066
REMINDER_SIZE_IN = 0.066
LABEL_SIZE_IN = 0.058
VALUE_SIZE_IN = 0.093
LINE_SPACING = 1.30
TRACKING_IN = 0.018
BODY_PANEL_MAX_IN = 1.52
#: How opaque the parchment plates are over the art. The backdrop under each
#: plate is blurred and dimmed first, which is what keeps text readable at an
#: alpha this low -- raise it with --panel-alpha if a table finds it thin.
PANEL_ALPHA = 186

# --- Palette ----------------------------------------------------------------
# Lifted off the card back: indigo ink, aged parchment, worn gold.
INK = (17, 36, 60)
INK_SOFT = (58, 76, 99)
PARCHMENT = (241, 233, 214)
GOLD = (176, 138, 66)
SHADOW = (8, 16, 28)

#: Each estate gets a keyline colour so a hand sorts by eye.
ESTATE_COLOURS: dict[str, tuple[int, int, int]] = {
    "Church": (122, 92, 158),
    "Military": (158, 62, 54),
    "Merchant": (42, 106, 112),
    "Commons": (150, 90, 42),
}
NEUTRAL_ACCENT = (96, 106, 126)

# --- Fonts ------------------------------------------------------------------
FONT_DIRS = (
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
    "C:/Windows/Fonts",
    str(Path.home() / ".fonts"),
    str(Path.home() / "Library/Fonts"),
)
SERIF_REGULAR = ("DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "Georgia.ttf", "times.ttf", "Times New Roman.ttf")
SERIF_BOLD = ("DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf", "Georgiab.ttf", "timesbd.ttf", "Times New Roman Bold.ttf")
SERIF_ITALIC = ("DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf", "Georgiai.ttf", "timesi.ttf", "Times New Roman Italic.ttf")


class Fonts:
    """Resolves a serif family once and caches every size it is asked for."""

    def __init__(self, extra_dirs: tuple[str, ...] = ()) -> None:
        self._dirs = tuple(extra_dirs) + FONT_DIRS
        self._index: dict[str, Path] | None = None
        self._cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        self.regular = self._resolve(SERIF_REGULAR, "regular")
        self.bold = self._resolve(SERIF_BOLD, "bold")
        self.italic = self._resolve(SERIF_ITALIC, "italic")

    def _scan(self) -> dict[str, Path]:
        if self._index is None:
            index: dict[str, Path] = {}
            for directory in self._dirs:
                root = Path(directory)
                if not root.is_dir():
                    continue
                for path in root.rglob("*"):
                    if path.suffix.lower() in (".ttf", ".otf"):
                        index.setdefault(path.name.lower(), path)
            self._index = index
        return self._index

    def _resolve(self, candidates: tuple[str, ...], style: str) -> Path | None:
        index = self._scan()
        for name in candidates:
            hit = index.get(name.lower())
            if hit is not None:
                return hit
        # Anything serif will do before we fall back to a bitmap face.
        for name, path in sorted(index.items()):
            if "serif" in name and style in name:
                return path
        for name, path in sorted(index.items()):
            if "serif" in name:
                return path
        return None

    def at(self, style: str, size_px: int) -> ImageFont.FreeTypeFont:
        size_px = max(1, size_px)
        key = (style, size_px)
        if key not in self._cache:
            path = getattr(self, style) or self.regular
            if path is None:  # pragma: no cover - only on a font-less box
                self._cache[key] = ImageFont.load_default()
            else:
                self._cache[key] = ImageFont.truetype(str(path), size_px)
        return self._cache[key]


# --- Drawing helpers --------------------------------------------------------
def cover(image: Image.Image, size: tuple[int, int], top_bias: float = 0.35) -> Image.Image:
    """Scale and crop `image` to fill `size` exactly, keeping its aspect.

    The art is a touch taller than a card, so the crop eats a sliver of the top
    and bottom. `top_bias` below 0.5 keeps more of the top, where heads live.
    """

    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    scaled = image.resize(
        (max(target_w, round(image.width * scale)), max(target_h, round(image.height * scale))),
        Image.LANCZOS,
    )
    left = round((scaled.width - target_w) / 2)
    top = round((scaled.height - target_h) * top_bias)
    return scaled.crop((left, top, left + target_w, top + target_h))


def tracked_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, tracking: int) -> float:
    if not text:
        return 0.0
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    tracking: int,
) -> None:
    """Letter-spaced text, drawn from a left/top origin. Pillow has no tracking."""

    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def typeset(text: str) -> str:
    """The prose in this repo is written with `--`; a card prints an em dash."""

    return text.replace(" -- ", " \u2014 ").replace("--", "\u2014")


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in typeset(text).split("\n"):
        words, line = paragraph.split(), ""
        for word in words:
            probe = f"{line} {word}".strip()
            if line and draw.textlength(probe, font=font) > max_width:
                lines.append(line)
                line = word
            else:
                line = probe
        lines.append(line)
    return lines


def fit_title(
    draw: ImageDraw.ImageDraw,
    name: str,
    fonts: Fonts,
    max_width: float,
    base_px: int,
    min_px: int,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Largest size at which the name fits on one line, else two."""

    for size in range(base_px, min_px - 1, -2):
        font = fonts.at("bold", size)
        if draw.textlength(name, font=font) <= max_width:
            return font, [name]
    for size in range(base_px, min_px - 1, -2):
        font = fonts.at("bold", size)
        lines = wrap(draw, name, font, max_width)
        if len(lines) <= 2 and all(draw.textlength(line, font=font) <= max_width for line in lines):
            return font, lines
    font = fonts.at("bold", min_px)
    return font, wrap(draw, name, font, max_width)


def blend(base: tuple[int, int, int], tint: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(b + (t - b) * amount) for b, t in zip(base, tint))  # type: ignore[return-value]


def border_colour(accent: tuple[int, int, int]) -> tuple[int, int, int]:
    """A darkened ink, pulled towards the estate, so a hand sorts by edge alone.

    Mixing ink and the estate colour at full strength lands on a washed-out
    mid-tone; taking the mix down to roughly three-quarters brightness keeps
    each estate distinguishable while the border still reads as near-black at
    arm's length, which is what a border is for.
    """

    return blend(blend(INK, accent, 0.45), (0, 0, 0), 0.28)


def window_size(layout: Layout) -> tuple[int, int]:
    """The area inside the border -- what the art actually gets to fill."""

    band = layout.px(BORDER_IN)
    width, height = layout.size
    return width - 2 * band, height - 2 * band


def framed(layout: Layout, accent: tuple[int, int, int], window: Image.Image) -> Image.Image:
    """Border fill, `window` inset into it, and a gold keyline along the seam.

    The art is fitted to the window rather than to the whole card and then
    covered over: painting a border on top of a full-bleed image throws away
    the outer 0.22 in of every illustration, which on the card back was enough
    to eat the last letter of the title.
    """

    width, height = layout.size
    band = layout.px(BORDER_IN)
    canvas = Image.new("RGBA", (width, height), border_colour(accent) + (255,))
    canvas.paste(window.convert("RGBA"), (band, band))

    keyline = max(2, layout.px(0.011))
    gold = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(gold).rectangle(
        (band - keyline, band - keyline, width - band + keyline - 1, height - band + keyline - 1),
        outline=GOLD + (255,),
        width=keyline,
    )
    canvas.alpha_composite(gold)
    return canvas


def plate(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    accent: tuple[int, int, int],
    alpha: int = PANEL_ALPHA,
) -> None:
    """A translucent parchment panel over a blurred, dimmed patch of the art.

    Treating the backdrop is what makes the translucency work: the art still
    reads through the panel, but it stops competing with the text on top of it,
    so the parchment can sit well below opaque and the type stays crisp.
    """

    x0, y0, x1, y1 = box
    blur = max(2, radius // 2)

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x0, y0 + blur, x1, y1 + blur), radius=radius, fill=SHADOW + (110,)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur)))

    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=radius, fill=255)
    backdrop = canvas.crop(box).filter(ImageFilter.GaussianBlur(max(3, radius)))
    backdrop = Image.blend(backdrop, Image.new("RGBA", backdrop.size, INK + (255,)), 0.22)
    canvas.paste(backdrop, (x0, y0), mask)

    panel = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle(box, radius=radius, fill=PARCHMENT + (alpha,))
    draw.rounded_rectangle(box, radius=radius, outline=accent + (235,), width=max(2, radius // 7))
    canvas.alpha_composite(panel)


# --- Card composition -------------------------------------------------------
@dataclass
class Layout:
    """Every measurement for one card, in pixels at the chosen DPI."""

    dpi: int

    def px(self, inches: float) -> int:
        return round(inches * self.dpi)

    @property
    def size(self) -> tuple[int, int]:
        return self.px(BLEED_W_IN), self.px(BLEED_H_IN)


def accent_for(card: CardDef) -> tuple[int, int, int]:
    estate = card.estate.value if card.estate else None
    return ESTATE_COLOURS.get(estate or "", NEUTRAL_ACCENT)


def courtier_attributes(card: CardDef) -> list[tuple[str, str]]:
    courtier = COURTIERS_BY_NAME[card.name]
    origin = courtier.origin.value
    if courtier.origin is Origin.BARBARIAN and courtier.people is not People.NONE:
        origin = f"{origin} \u00b7 {courtier.people.value}"
    house = "None" if courtier.family is Family.NONE else courtier.family.value
    return [
        ("Estate", courtier.estate.value),
        ("Faith", courtier.faith.value),
        ("House", house),
        ("Origin", origin),
    ]


def render_front(card: CardDef, art_path: Path, layout: Layout, fonts: Fonts, alpha: int) -> Image.Image:
    width, height = layout.size
    content = layout.px(CONTENT_IN)
    pad = layout.px(PLATE_PAD_IN)
    radius = layout.px(PLATE_RADIUS_IN)
    tracking = layout.px(TRACKING_IN)
    accent = accent_for(card)

    with Image.open(art_path) as art:
        window = cover(art.convert("RGB"), window_size(layout))
    canvas = framed(layout, accent, window)

    measure = ImageDraw.Draw(canvas)
    content_width = width - 2 * content
    inner_width = content_width - 2 * pad

    # --- Title plate: name, then the type line in tracked small caps --------
    # The plate is only as wide as the longer of the two lines needs, so a
    # short name covers a strip of the portrait rather than the whole band.
    name_font, name_lines = fit_title(
        measure, card.name, fonts, inner_width, layout.px(NAME_SIZE_IN), layout.px(NAME_MIN_SIZE_IN)
    )
    type_font = fonts.at("regular", layout.px(TYPE_SIZE_IN))
    type_text = card_text.type_line(card).upper()
    name_leading = round(name_font.size * 1.16)

    text_width = max(
        max(measure.textlength(line, font=name_font) for line in name_lines),
        tracked_width(measure, type_text, type_font, tracking),
    )
    title_width = min(content_width, round(text_width) + 2 * pad + layout.px(0.14))
    title_x0 = round((width - title_width) / 2)
    title_height = pad + len(name_lines) * name_leading + round(type_font.size * 1.6) + pad
    title_box = (title_x0, content, title_x0 + title_width, content + title_height)
    plate(canvas, title_box, radius, accent, alpha)

    draw = ImageDraw.Draw(canvas)
    y = content + pad
    for line in name_lines:
        draw.text(((width - draw.textlength(line, font=name_font)) / 2, y), line, font=name_font, fill=INK)
        y += name_leading
    y += round(type_font.size * 0.22)
    draw_tracked(
        draw,
        ((width - tracked_width(draw, type_text, type_font, tracking)) / 2, y),
        type_text,
        type_font,
        accent,
        tracking,
    )

    # --- Bottom plate: attributes for a courtier, rules for everything else -
    if card.is_courtier:
        body = render_attribute_plate(canvas, card, layout, fonts, accent)
    else:
        body = render_rules_plate(canvas, card, layout, fonts, accent)

    plate(canvas, body, radius, accent, alpha)
    if card.is_courtier:
        fill_attribute_plate(canvas, card, body, layout, fonts, accent)
    else:
        fill_rules_plate(canvas, card, body, layout, fonts, accent)
    return canvas.convert("RGB")


def rules_block(card: CardDef, layout: Layout, fonts: Fonts, measure: ImageDraw.ImageDraw, inner_width: int):
    """Shrink the rules text until the plate fits under BODY_PANEL_MAX_IN."""

    text = card_text.rules_for(card)
    reminder = card_text.REMINDERS.get(card.kind, "")
    pad = layout.px(PLATE_PAD_IN)
    for size in range(layout.px(BODY_SIZE_IN), layout.px(BODY_MIN_SIZE_IN) - 1, -1):
        font = fonts.at("regular", size)
        lines = wrap(measure, text, font, inner_width)
        leading = round(size * LINE_SPACING)
        reminder_font = fonts.at("italic", round(size * REMINDER_SIZE_IN / BODY_SIZE_IN))
        reminder_lines = wrap(measure, reminder, reminder_font, inner_width) if reminder else []
        height = (
            pad
            + len(lines) * leading
            + (round(leading * 0.45) + len(reminder_lines) * round(reminder_font.size * 1.25) if reminder_lines else 0)
            + pad
        )
        if height <= layout.px(BODY_PANEL_MAX_IN):
            break
    return font, lines, leading, reminder_font, reminder_lines, height


def render_rules_plate(canvas, card, layout, fonts, accent) -> tuple[int, int, int, int]:
    width, height = canvas.size
    content, pad = layout.px(CONTENT_IN), layout.px(PLATE_PAD_IN)
    measure = ImageDraw.Draw(canvas)
    *_, plate_height = rules_block(card, layout, fonts, measure, width - 2 * content - 2 * pad)
    return (content, height - content - plate_height, width - content, height - content)


def fill_rules_plate(canvas, card, box, layout, fonts, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    content, pad = layout.px(CONTENT_IN), layout.px(PLATE_PAD_IN)
    inner_width = canvas.width - 2 * content - 2 * pad
    font, lines, leading, reminder_font, reminder_lines, _ = rules_block(card, layout, fonts, draw, inner_width)

    x, y = box[0] + pad, box[1] + pad
    for line in lines:
        draw.text((x, y), line, font=font, fill=INK)
        y += leading
    if reminder_lines:
        y += round(leading * 0.18)
        rule_y = y + round(leading * 0.12)
        draw.line((x, rule_y, box[2] - pad, rule_y), fill=accent + (160,), width=max(1, layout.px(0.004)))
        y += round(leading * 0.30)
        for line in reminder_lines:
            draw.text((x, y), line, font=reminder_font, fill=INK_SOFT)
            y += round(reminder_font.size * 1.25)


def render_attribute_plate(canvas, card, layout, fonts, accent) -> tuple[int, int, int, int]:
    width, height = canvas.size
    content, pad = layout.px(CONTENT_IN), layout.px(PLATE_PAD_IN)
    row = layout.px(LABEL_SIZE_IN) + layout.px(VALUE_SIZE_IN) + layout.px(0.086)
    plate_height = pad + 2 * row - layout.px(0.034) + pad
    return (content, height - content - plate_height, width - content, height - content)


def fill_attribute_plate(canvas, card, box, layout, fonts, accent) -> None:
    """Two columns, two rows: estate and faith over house and origin."""

    draw = ImageDraw.Draw(canvas)
    pad = layout.px(PLATE_PAD_IN)
    tracking = layout.px(TRACKING_IN * 0.8)
    label_font = fonts.at("regular", layout.px(LABEL_SIZE_IN))
    value_font = fonts.at("bold", layout.px(VALUE_SIZE_IN))
    row = layout.px(LABEL_SIZE_IN) + layout.px(VALUE_SIZE_IN) + layout.px(0.086)

    column_width = (box[2] - box[0] - 2 * pad) / 2
    mid_x = box[0] + pad + column_width
    draw.line(
        (mid_x, box[1] + pad, mid_x, box[3] - pad),
        fill=accent + (90,),
        width=max(1, layout.px(0.004)),
    )

    for i, (label, value) in enumerate(courtier_attributes(card)):
        column, line = i % 2, i // 2
        x = box[0] + pad + column * column_width + (layout.px(0.055) if column else 0)
        y = box[1] + pad + line * row
        draw_tracked(draw, (x, y), label.upper(), label_font, accent, tracking)
        value_y = y + layout.px(LABEL_SIZE_IN) + layout.px(0.030)
        value_size = value_font
        while draw.textlength(value, font=value_size) > column_width - layout.px(0.07) and value_size.size > 10:
            value_size = fonts.at("bold", value_size.size - 2)
        draw.text((x, value_y), value, font=value_size, fill=INK)


def render_agenda(name: str, subtitle: str, text: str, layout: Layout, fonts: Fonts) -> Image.Image:
    """A text-only agenda card: parchment inside the same border as the rest.

    No art was drawn for the agendas, so these are set type on parchment. They
    take the border anyway, both so a revealed agenda looks like it belongs to
    the deck and so the backs line up in the same order.
    """

    width, height = layout.size
    content, pad = layout.px(CONTENT_IN), layout.px(PLATE_PAD_IN)
    inner_width = width - 2 * content
    tracking = layout.px(TRACKING_IN)

    canvas = framed(layout, NEUTRAL_ACCENT, Image.new("RGB", window_size(layout), PARCHMENT))
    draw = ImageDraw.Draw(canvas)

    label_font = fonts.at("regular", layout.px(TYPE_SIZE_IN))
    name_font, name_lines = fit_title(
        draw, name, fonts, inner_width - 2 * pad, layout.px(NAME_SIZE_IN * 1.15), layout.px(NAME_MIN_SIZE_IN)
    )
    name_leading = round(name_font.size * 1.18)
    band_top = layout.px(BORDER_IN)
    band_height = round(label_font.size * 2.4) + len(name_lines) * name_leading + layout.px(0.16)
    draw.rectangle((band_top, band_top, width - band_top, band_top + band_height), fill=INK)
    rule = max(2, layout.px(0.010))
    draw.rectangle(
        (band_top, band_top + band_height, width - band_top, band_top + band_height + rule), fill=GOLD
    )

    label = "AGENDA"
    y = band_top + layout.px(0.10)
    draw_tracked(
        draw,
        ((width - tracked_width(draw, label, label_font, tracking)) / 2, y),
        label,
        label_font,
        GOLD,
        tracking,
    )
    y += round(label_font.size * 2.2)
    for line in name_lines:
        draw.text(((width - draw.textlength(line, font=name_font)) / 2, y), line, font=name_font, fill=PARCHMENT)
        y += name_leading

    body_font = fonts.at("regular", layout.px(BODY_SIZE_IN * 1.18))
    body_leading = round(body_font.size * LINE_SPACING)
    lines = wrap(draw, text, body_font, inner_width - 2 * pad)
    reminder = (
        "Reveal and win the moment the board shows this. Two agendas can be "
        "satisfied at once; both players win."
    )
    reminder_font = fonts.at("italic", layout.px(REMINDER_SIZE_IN))
    reminder_lines = wrap(draw, reminder, reminder_font, inner_width - 2 * pad)
    sub_font = fonts.at("italic", layout.px(BODY_SIZE_IN * 1.25))

    # Flavour is pinned above the border; the condition floats in what is left,
    # a little above centre so the card does not read as bottom-heavy.
    subtitle_y = height - content - round(sub_font.size * 1.6)
    block = (
        len(lines) * body_leading
        + layout.px(0.30)
        + len(reminder_lines) * round(reminder_font.size * 1.28)
    )
    region_top = band_top + band_height + rule
    y = region_top + max(layout.px(0.22), round((subtitle_y - region_top - block) * 0.42))
    for line in lines:
        draw.text((content + pad, y), line, font=body_font, fill=INK)
        y += body_leading

    y += layout.px(0.15)
    draw.line((content + pad, y, width - content - pad, y), fill=GOLD, width=max(1, layout.px(0.005)))
    y += layout.px(0.15)
    for line in reminder_lines:
        draw.text((content + pad, y), line, font=reminder_font, fill=INK_SOFT)
        y += round(reminder_font.size * 1.28)

    draw.text(
        ((width - draw.textlength(subtitle, font=sub_font)) / 2, subtitle_y),
        subtitle,
        font=sub_font,
        fill=INK_SOFT,
    )
    return canvas.convert("RGB")


def render_seat(
    seat: Seat,
    layout: Layout,
    fonts: Fonts,
    art_path: Path | None = None,
    alpha: int = PANEL_ALPHA,
) -> Image.Image:
    """A seat card: the chair itself, laid on the table for courtiers to fill.

    Bordered in its estate's colour like the courtiers that may sit in it, so
    a player matches card to chair by edge without reading either.

    With `art_path` -- an empty throne, per the prompts in `art/` -- it is laid
    out like any other card. Without, it falls back to type on parchment, so
    the board is printable before the seat art has been generated.
    """

    if art_path is not None:
        return render_seat_with_art(seat, art_path, layout, fonts, alpha)

    width, height = layout.size
    content, pad = layout.px(CONTENT_IN), layout.px(PLATE_PAD_IN)
    inner_width = width - 2 * content
    tracking = layout.px(TRACKING_IN)
    accent = ESTATE_COLOURS[SEAT_ESTATE[seat].value]

    canvas = framed(layout, accent, Image.new("RGB", window_size(layout), PARCHMENT))
    draw = ImageDraw.Draw(canvas)

    label_font = fonts.at("regular", layout.px(TYPE_SIZE_IN))
    name_font, name_lines = fit_title(
        draw, seat.value, fonts, inner_width - 2 * pad, layout.px(NAME_SIZE_IN * 1.2),
        layout.px(NAME_MIN_SIZE_IN),
    )
    name_leading = round(name_font.size * 1.18)
    band_top = layout.px(BORDER_IN)
    band_height = round(label_font.size * 2.4) + len(name_lines) * name_leading + layout.px(0.16)
    draw.rectangle((band_top, band_top, width - band_top, band_top + band_height), fill=INK)
    rule = max(2, layout.px(0.010))
    draw.rectangle(
        (band_top, band_top + band_height, width - band_top, band_top + band_height + rule),
        fill=accent,
    )

    label = card_text.seat_type_line(seat).upper()
    y = band_top + layout.px(0.10)
    draw_tracked(
        draw,
        ((width - tracked_width(draw, label, label_font, tracking)) / 2, y),
        label,
        label_font,
        blend(accent, PARCHMENT, 0.45),
        tracking,
    )
    y += round(label_font.size * 2.2)
    for line in name_lines:
        draw.text(((width - draw.textlength(line, font=name_font)) / 2, y), line, font=name_font, fill=PARCHMENT)
        y += name_leading

    body_font = fonts.at("regular", layout.px(BODY_SIZE_IN * 1.12))
    body_leading = round(body_font.size * LINE_SPACING)
    lines = wrap(draw, card_text.SEAT_TEXT[seat], body_font, inner_width - 2 * pad)
    reminder_font = fonts.at("italic", layout.px(REMINDER_SIZE_IN))
    reminder_lines = wrap(draw, card_text.SEAT_REMINDER, reminder_font, inner_width - 2 * pad)

    # The lower half is left clear: this is where the courtier goes.
    y = band_top + band_height + rule + layout.px(0.26)
    for line in lines:
        draw.text((content + pad, y), line, font=body_font, fill=INK)
        y += body_leading
    y += layout.px(0.16)
    draw.line((content + pad, y, width - content - pad, y), fill=accent, width=max(1, layout.px(0.005)))
    y += layout.px(0.15)
    for line in reminder_lines:
        draw.text((content + pad, y), line, font=reminder_font, fill=INK_SOFT)
        y += round(reminder_font.size * 1.28)

    place = "PLACE THE SEATED COURTIER HERE"
    place_font = fonts.at("regular", layout.px(LABEL_SIZE_IN))
    draw_tracked(
        draw,
        ((width - tracked_width(draw, place, place_font, tracking)) / 2,
         height - content - round(place_font.size * 2.0)),
        place,
        place_font,
        blend(INK_SOFT, PARCHMENT, 0.35),
        tracking,
    )
    return canvas.convert("RGB")


def render_seat_with_art(
    seat: Seat, art_path: Path, layout: Layout, fonts: Fonts, alpha: int
) -> Image.Image:
    """The seat card once its empty throne has been drawn.

    Same furniture as an action card -- title plate above, rules plate below,
    art between -- so a seat reads as part of the same deck.
    """

    width, height = layout.size
    content, pad = layout.px(CONTENT_IN), layout.px(PLATE_PAD_IN)
    radius = layout.px(PLATE_RADIUS_IN)
    tracking = layout.px(TRACKING_IN)
    accent = ESTATE_COLOURS[SEAT_ESTATE[seat].value]

    with Image.open(art_path) as art:
        window = cover(art.convert("RGB"), window_size(layout))
    canvas = framed(layout, accent, window)

    measure = ImageDraw.Draw(canvas)
    content_width = width - 2 * content
    inner_width = content_width - 2 * pad

    name_font, name_lines = fit_title(
        measure, seat.value, fonts, inner_width, layout.px(NAME_SIZE_IN), layout.px(NAME_MIN_SIZE_IN)
    )
    type_font = fonts.at("regular", layout.px(TYPE_SIZE_IN))
    type_text = card_text.seat_type_line(seat).upper()
    name_leading = round(name_font.size * 1.16)
    text_width = max(
        max(measure.textlength(line, font=name_font) for line in name_lines),
        tracked_width(measure, type_text, type_font, tracking),
    )
    title_width = min(content_width, round(text_width) + 2 * pad + layout.px(0.14))
    title_x0 = round((width - title_width) / 2)
    title_height = pad + len(name_lines) * name_leading + round(type_font.size * 1.6) + pad
    title_box = (title_x0, content, title_x0 + title_width, content + title_height)
    plate(canvas, title_box, radius, accent, alpha)

    draw = ImageDraw.Draw(canvas)
    y = content + pad
    for line in name_lines:
        draw.text(((width - draw.textlength(line, font=name_font)) / 2, y), line, font=name_font, fill=INK)
        y += name_leading
    y += round(type_font.size * 0.22)
    draw_tracked(
        draw,
        ((width - tracked_width(draw, type_text, type_font, tracking)) / 2, y),
        type_text,
        type_font,
        accent,
        tracking,
    )

    body_font = fonts.at("regular", layout.px(BODY_SIZE_IN))
    leading = round(body_font.size * LINE_SPACING)
    lines = wrap(draw, card_text.SEAT_TEXT[seat], body_font, inner_width)
    body_height = pad + len(lines) * leading + pad
    body = (content, height - content - body_height, width - content, height - content)
    plate(canvas, body, radius, accent, alpha)

    draw = ImageDraw.Draw(canvas)
    y = body[1] + pad
    for line in lines:
        draw.text((content + pad, y), line, font=body_font, fill=INK)
        y += leading
    return canvas.convert("RGB")


# --- Order file -------------------------------------------------------------
#: What goes in the zip beside the cards, so somebody who has never used the
#: desktop tool can still get from download to order.
ZIP_README = """Court of Succession -- print-ready deck
======================================

{count} cards for MakePlayingCards, {dpi} DPI, 2.72 x 3.70 in with bleed.

1. Download the `autofill` executable for your platform:
   https://github.com/chilli-axe/mpc-autofill/releases
2. Put it in this folder, beside succession.xml.
3. Run it. On Linux, from a terminal: ./autofill-linux.bin
   On macOS, allow it once in System Settings > Privacy & Security.
4. Sign in to MakePlayingCards with an account made on their site --
   the automated browser cannot do a Google sign-in.

It uploads every card, sets the stock and the bracket, and leaves the
project in your MPC cart. Check the preview before you pay.

succession.xml points at `cards/...` relative to itself, so keep the two
together and run the executable from this folder.

Cardstock is set to {stock}. To change it, edit the <stock> line in
succession.xml, or rebuild with: python tools/mpcfill.py --stock "..."
"""


def build_xml(
    slots: list[tuple[Path, str]],
    cardback: Path,
    stock: str,
    foil: bool,
    relative_to: Path | None = None,
) -> str:
    """One `<card>` per slot, pointing at an absolute path on this machine.

    `sourceType` of `Local File` is what stops the desktop tool treating the
    path as a Google Drive id; the cardback tag has no room for a source type,
    but the tool infers one when the text is a path that exists.

    `relative_to` writes each path relative to that directory instead of
    absolute, which is what makes the zip portable: the desktop tool resolves a
    local path against its own working directory, so an order unzipped anywhere
    still finds its cards as long as the executable is run beside the XML.
    """

    def reference(path: Path) -> str:
        if relative_to is None:
            return str(path)
        return path.relative_to(relative_to).as_posix()

    order = ET.Element("order")
    details = ET.SubElement(order, "details")
    ET.SubElement(details, "quantity").text = str(len(slots))
    ET.SubElement(details, "stock").text = stock
    ET.SubElement(details, "foil").text = "true" if foil else "false"

    fronts = ET.SubElement(order, "fronts")
    for slot, (path, query) in enumerate(slots):
        card = ET.SubElement(fronts, "card")
        ET.SubElement(card, "id").text = reference(path)
        ET.SubElement(card, "sourceType").text = "Local File"
        ET.SubElement(card, "slots").text = str(slot)
        ET.SubElement(card, "name").text = path.name
        ET.SubElement(card, "query").text = query
    ET.SubElement(order, "cardback").text = reference(cardback)

    raw = ET.tostring(order, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="    ")


def write_zip(
    path: Path,
    mpc_dir: Path,
    slots: list[tuple[Path, str]],
    cardback: Path,
    stock: str,
    foil: bool,
    dpi: int,
) -> Path:
    """A folder somebody can download, unzip anywhere, and order from.

    The order file inside points at `cards/...` relative to itself rather than
    at absolute paths on the machine that built it, which is the whole reason
    this is a separate artifact and not just a zip of `build/mpc`.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    order = build_xml(slots, cardback, stock, foil, relative_to=mpc_dir)
    readme = ZIP_README.format(count=len(slots) + 1, dpi=dpi, stock=stock)

    seen: set[str] = set()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("succession.xml", order)
        archive.writestr("HOW TO PRINT.txt", readme)
        for card_path, _ in list(slots) + [(cardback, "")]:
            name = f"cards/{card_path.name}"
            if name in seen:  # the one cardback is shared by every slot
                continue
            seen.add(name)
            archive.write(card_path, name)
    return path


# --- CLI --------------------------------------------------------------------
def trimmed(full: Image.Image, layout: Layout, target_dpi: int) -> Image.Image:
    """The card as it comes back from the cutter, at a size a browser wants.

    The bleed is there for the blade, not for a reader: on screen it just adds
    a band of art that nobody's copy of the card has. So the web rendition
    crops it off and scales what is left.
    """

    bleed = layout.px(BLEED_MARGIN_IN)
    width, height = full.size
    card = full.crop((bleed, bleed, width - bleed, height - bleed))
    if target_dpi != layout.dpi:
        scale = target_dpi / layout.dpi
        card = card.resize((round(card.width * scale), round(card.height * scale)), Image.LANCZOS)
    return card


def save(image: Image.Image, path: Path, fmt: str, quality: int, dpi: int) -> Path:
    """Write the file, stamping the DPI it was actually rendered at.

    MPC Autofill works DPI out from pixel height and ignores the metadata, but
    anyone who opens the file in an editor reads this.
    """

    path = path.with_suffix(f".{fmt}")
    if fmt == "jpg":
        image.save(path, "JPEG", quality=quality, subsampling=0, dpi=(dpi, dpi))
    else:
        image.save(path, "PNG", dpi=(dpi, dpi))
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose card fronts from assets/ into a print and a web rendition.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "The print rendition goes to <out>/mpc: full bleed, for the MPC Autofill\n"
            "`autofill` executable, which you put next to the generated .xml and run.\n"
            "The web rendition goes to <out>/web: trimmed, browser-sized, with an\n"
            "index.html that shows the deck. See docs/PRINTING.md."
        ),
    )
    parser.add_argument("--assets", type=Path, default=REPO_ROOT / "assets", help="where the art lives")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "build", help="output directory")
    parser.add_argument(
        "--profile",
        default="print,web",
        metavar="print,web,docs",
        help=(
            "comma-separated renditions to build: print (full bleed for MPC), "
            "web (trimmed, browsable), docs (thumbnails and docs/CARDS.md). "
            "'all' builds every one. Default print,web"
        ),
    )
    parser.add_argument(
        "--zip",
        dest="make_zip",
        action="store_true",
        help="also write a portable zip of the print cards and a relative-path order file",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=REPO_ROOT / "docs",
        help="where the docs rendition writes CARDS.md and its thumbnails",
    )
    parser.add_argument(
        "--docs-dpi", type=int, default=110, help="thumbnail resolution for the docs rendition"
    )
    parser.add_argument(
        "--zip-link",
        default="",
        help="URL for the download line at the top of docs/CARDS.md",
    )
    parser.add_argument("--dpi", type=int, default=600, help="print resolution (default 600; MPC needs 300+)")
    parser.add_argument("--format", choices=("png", "jpg"), default="png", help="print image format")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality when --format jpg")
    parser.add_argument("--web-dpi", type=int, default=300, help="web resolution (default 300: 744px wide)")
    parser.add_argument("--web-quality", type=int, default=85, help="JPEG quality for the web rendition")
    parser.add_argument(
        "--stock",
        default="(S30) Standard Smooth",
        help="MPC cardstock: (S27) Smooth, (S30) Standard Smooth, (S33) Superior Smooth, (M31) Linen, (P10) Plastic",
    )
    parser.add_argument("--foil", action="store_true", help="order foil fronts")
    parser.add_argument("--outmaneuver-copies", type=int, default=1, help="copies of Outmaneuver in the deck")
    parser.add_argument(
        "--no-agendas",
        dest="include_agendas",
        action="store_false",
        help="leave out the 8 agenda cards, for an 84-card order in a smaller bracket",
    )
    parser.add_argument(
        "--no-seats",
        dest="include_seats",
        action="store_false",
        help="leave out the 7 seat cards that make up the board",
    )
    parser.add_argument(
        "--panel-alpha",
        type=int,
        default=PANEL_ALPHA,
        metavar="0-255",
        help=f"how opaque the text plates are over the art (default {PANEL_ALPHA})",
    )
    parser.add_argument("--only", help="comma-separated asset numbers to re-render, e.g. 26,41")
    parser.add_argument("--font-dir", action="append", default=[], help="extra directory to search for fonts")
    args = parser.parse_args(argv)

    known = {"print", "web", "docs"}
    chosen = known if args.profile == "all" else {p.strip() for p in args.profile.split(",") if p.strip()}
    if args.profile == "both":  # the spelling this flag used to take
        chosen = {"print", "web"}
    if chosen - known:
        parser.error(f"unknown profile: {', '.join(sorted(chosen - known))}")
    want_print, want_web, want_docs = ("print" in chosen), ("web" in chosen), ("docs" in chosen)
    if not chosen:
        parser.error("--profile needs at least one of print, web, docs")
    if args.make_zip and not want_print:
        parser.error("--zip needs the print rendition; add print to --profile")
    if want_print and args.dpi < 300:
        parser.error(f"--dpi {args.dpi} is below MakePlayingCards' 300 DPI minimum")
    if not 0 <= args.panel_alpha <= 255:
        parser.error("--panel-alpha takes a value from 0 (invisible) to 255 (opaque)")
    if want_print and args.dpi > MAX_USEFUL_DPI:
        print(f"note: the desktop tool downscales above {MAX_USEFUL_DPI} DPI, so {args.dpi} buys nothing")

    # Compose once, at whichever resolution is the more demanding, and let the
    # web rendition be a trim and a downscale of it. Rendering the deck twice
    # would cost twice the time and risk the two drifting apart.
    layout = Layout(args.dpi if want_print else max(args.web_dpi if want_web else 0, args.docs_dpi))
    fonts = Fonts(tuple(args.font_dir))
    if fonts.regular is None:
        print("warning: no serif TrueType font found; text will fall back to a bitmap face")

    cards = build_cards(args.outmaneuver_copies)
    by_index = scan(args.assets)
    if 0 not in by_index:
        raise SystemExit(f"No card back found at {args.assets / '00_cardback.png'}")
    try:
        chosen = map_to_deck(cards, by_index)
    except AssetMismatch as mismatch:
        raise SystemExit(str(mismatch)) from None

    print_dir = args.out / "mpc" / "cards"
    web_dir = args.out / "web" / "cards"
    docs_dir = args.docs_dir / "cards"
    for directory, wanted in ((print_dir, want_print), (web_dir, want_web), (docs_dir, want_docs)):
        if wanted:
            directory.mkdir(parents=True, exist_ok=True)
    only = {int(n) for n in args.only.split(",")} if args.only else None

    def emit(image: Image.Image | None, stem: str, slug: str) -> tuple[Path, str, str]:
        """Write a composed card to whichever renditions were asked for.

        The docs thumbnails take a slugged name rather than the printed one:
        they end up in a Markdown table committed to the repository, where a
        filename with spaces in it is a URL nobody wants to read.
        """

        printed = (print_dir / stem).with_suffix(f".{args.format}")
        web = (web_dir / stem).with_suffix(".jpg")
        doc = (docs_dir / slug).with_suffix(".jpg")
        if image is not None:
            if want_print:
                printed = save(image, printed, args.format, args.quality, args.dpi)
            if want_web:
                web = save(
                    trimmed(image, layout, args.web_dpi), web, "jpg", args.web_quality, args.web_dpi
                )
            if want_docs:
                # Rendered at twice the width it is displayed at, so the table
                # stays sharp on a high-density screen.
                doc = save(
                    trimmed(image, layout, args.docs_dpi), doc, "jpg", args.web_quality, args.docs_dpi
                )
        return printed.resolve(), web.name, doc.name

    slots: list[tuple[Path, str]] = []
    entries: list[gallery.Entry] = []
    rows: list[cardlist.Row] = []
    alternates: list[str] = []
    for slot, (card, asset) in enumerate(zip(cards, chosen)):
        stem = f"{asset.index:02d} {card.name}"
        slug = f"{asset.index:02d}-{cardlist.slugify(card.name)}"
        wanted = only is None or asset.index in only
        image = render_front(card, asset.path, layout, fonts, args.panel_alpha) if wanted else None
        printed, web_name, doc_name = emit(image, stem, slug)
        if wanted:
            print(f"  [{slot:>2}] {stem}")
        if len(by_index[asset.index]) > 1:
            alternates.append(f"{asset.index:02d} {card.name} ({len(by_index[asset.index])} versions)")
        slots.append((printed, card.name.lower()))
        type_line = card_text.type_line(card)
        entries.append(
            gallery.Entry(
                slot=slot,
                label=f"{asset.index:02d}",
                name=card.name,
                type_line=type_line,
                filename=web_name,
                group=card.kind.value,
            )
        )
        rows.append(
            cardlist.Row(
                label=f"Card {asset.index:02d}",
                name=card.name,
                type_line=type_line,
                detail=(
                    " \u00b7 ".join(value for _, value in courtier_attributes(card))
                    if card.is_courtier
                    else card_text.rules_for(card)
                ),
                image=f"cards/{doc_name}",
                group=card.kind.value,
            )
        )

    if args.include_agendas:
        for i, (name, subtitle, text) in enumerate(card_text.AGENDA_TEXT, start=85):
            stem = f"{i:02d} {name.replace(':', ' --')}"
            slug = f"{i:02d}-{cardlist.slugify(name)}"
            wanted = only is None or i in only
            image = render_agenda(name, subtitle, text, layout, fonts) if wanted else None
            printed, web_name, doc_name = emit(image, stem, slug)
            if wanted:
                print(f"  [{len(slots):>2}] {stem}")
            slots.append((printed, name.lower()))
            entries.append(
                gallery.Entry(
                    slot=len(entries),
                    label=f"{i:02d}",
                    name=name,
                    type_line=subtitle,
                    filename=web_name,
                    group="Agenda",
                )
            )
            rows.append(
                cardlist.Row(
                    label=f"Card {i:02d}",
                    name=name,
                    type_line=subtitle,
                    detail=text,
                    image=f"cards/{doc_name}",
                    group="Agenda",
                )
            )

    if args.include_seats:
        # The board. Seven chairs, laid out on the table for courtiers to fill,
        # printed with the deck because the order is paid for by bracket: 92
        # cards and 99 both sit in the same one, so these cost nothing.
        for i, seat in enumerate(SEAT_ESTATE, start=len(slots) + 1):
            stem = f"{i:02d} Seat -- {seat.value}"
            slug = f"{i:02d}-seat-{cardlist.slugify(seat.value)}"
            wanted = only is None or i in only
            seat_art = by_index.get(i)
            image = (
                render_seat(
                    seat, layout, fonts,
                    seat_art[0].path if seat_art else None,
                    args.panel_alpha,
                )
                if wanted
                else None
            )
            printed, web_name, doc_name = emit(image, stem, slug)
            if wanted:
                print(f"  [{len(slots):>2}] {stem}")
            slots.append((printed, seat.value.lower()))
            entries.append(
                gallery.Entry(
                    slot=len(entries),
                    label=f"{i:02d}",
                    name=seat.value,
                    type_line=card_text.seat_type_line(seat),
                    filename=web_name,
                    group="Seat",
                )
            )
            rows.append(
                cardlist.Row(
                    label=f"Card {i:02d}",
                    name=seat.value,
                    type_line=card_text.seat_type_line(seat),
                    detail=card_text.SEAT_TEXT[seat],
                    image=f"cards/{doc_name}",
                    group="Seat",
                )
            )

    back_asset = by_index[0][0]
    back_image = None
    if only is None or 0 in only:
        with Image.open(back_asset.path) as art:
            window = cover(art.convert("RGB"), window_size(layout), top_bias=0.5)
        back_image = framed(layout, NEUTRAL_ACCENT, window).convert("RGB")
    back_path, back_web, back_doc = emit(back_image, "00 Cardback", "00-cardback")

    if want_print:
        mpc_dir = args.out / "mpc"
        xml_path = mpc_dir / "succession.xml"
        xml_path.write_text(build_xml(slots, back_path, args.stock, args.foil), encoding="utf-8")
        total_mb = sum(p.stat().st_size for p, _ in slots if p.exists()) / 1e6
        print(f"\nPrint: {len(slots)} fronts + 1 back at {args.dpi} DPI, full bleed ({total_mb:.0f} MB)")
        print(f"       {print_dir}")
        print(f"       order file -> {xml_path}")

        if args.make_zip:
            bundle = write_zip(
                args.out / "succession-print-deck.zip",
                mpc_dir,
                slots,
                back_path,
                args.stock,
                args.foil,
                args.dpi,
            )
            print(
                f"\nZip:   {bundle} ({bundle.stat().st_size / 1e6:.0f} MB)"
                "\n       cards + a relative-path order file, portable to any machine"
            )

    if want_docs and only is None:
        # A rename leaves the old thumbnail behind, and nothing downstream
        # would notice a stale file sitting in a committed directory.
        keep = {pathlib.Path(row.image).name for row in rows} | {back_doc}
        for orphan in sorted(p for p in docs_dir.glob("*.jpg") if p.name not in keep):
            orphan.unlink()
            print(f"  removed orphaned thumbnail: {orphan.name}")

    if want_docs:
        listing = cardlist.write(
            args.docs_dir / "CARDS.md",
            rows,
            cardlist.Row("Card 00", "Card back", "", "Shared by every card in the deck.",
                         f"cards/{back_doc}", "Card back"),
            args.zip_link or None,
        )
        docs_mb = sum(f.stat().st_size for f in docs_dir.glob("*.jpg")) / 1e6
        print(
            f"\nDocs:  {len(rows)} cards + 1 back at {round(TRIM_W_IN * args.docs_dpi)}px wide "
            f"({docs_mb:.0f} MB)\n       {listing}"
        )

    if want_web:
        index = gallery.write(
            args.out / "web" / "index.html",
            "Court of Succession",
            f"Playtest alpha \u00b7 {len(entries)} cards, trimmed as printed",
            entries,
            back_web,
        )
        web_mb = sum(f.stat().st_size for f in web_dir.glob("*.jpg")) / 1e6
        card_px = round(TRIM_W_IN * args.web_dpi)
        print(f"\nWeb:   {len(entries)} cards + 1 back at {card_px}px wide, trimmed ({web_mb:.0f} MB)")
        print(f"       {index}")

    if alternates:
        print("\nCards with more than one version of the art (the lowest-numbered one was used):")
        for line in alternates:
            print(f"  {line}")
    if want_print:
        print(
            "\nNext: put the MPC Autofill `autofill` executable in "
            f"{args.out / 'mpc'}, run it, and pick succession.xml."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
