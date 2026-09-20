#!/usr/bin/env python3
"""Compose print-ready card fronts and write an MPC Autofill order file.

The art in `assets/` is illustration only -- no name, no attributes, no rules
text -- so this script lays the printed card over it and then writes the XML
that MPC Autofill's desktop tool feeds to MakePlayingCards.

    python tools/mpcfill.py                       # build everything into build/mpc/
    python tools/mpcfill.py --dpi 300 --format jpg
    python tools/mpcfill.py --include-agendas     # add the 8 text-only agenda cards
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
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from xml.dom import minidom

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from succession.cards import CardDef, build_cards  # noqa: E402
from succession.courtiers import COURTIERS_BY_NAME  # noqa: E402
from succession.enums import Family, Origin, People  # noqa: E402
from tools import card_text  # noqa: E402
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
SAFE_IN = 0.20

#: The desktop tool reads an image's DPI as `300 * height / 1110`, i.e. it
#: expects exactly the 3.70 in of bleed height we render to, and downscales
#: anything above 800 DPI before upload.
assert abs(1110 / 300 - BLEED_H_IN) < 1e-9, "bleed height disagrees with the desktop tool"
MAX_USEFUL_DPI = 800

# Plate metrics, in inches. Everything else is derived from these.
PLATE_PAD_IN = 0.075
PLATE_RADIUS_IN = 0.055
NAME_SIZE_IN = 0.165
NAME_MIN_SIZE_IN = 0.098
TYPE_SIZE_IN = 0.070
BODY_SIZE_IN = 0.086
BODY_MIN_SIZE_IN = 0.066
REMINDER_SIZE_IN = 0.066
LABEL_SIZE_IN = 0.058
VALUE_SIZE_IN = 0.093
LINE_SPACING = 1.30
TRACKING_IN = 0.018
BODY_PANEL_MAX_IN = 1.52

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
    "Commons": (140, 112, 56),
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


def plate(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    accent: tuple[int, int, int],
    alpha: int = 243,
) -> None:
    """A parchment panel with a dropped shadow and a coloured hairline."""

    x0, y0, x1, y1 = box
    blur = max(2, radius // 2)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x0, y0 + blur, x1, y1 + blur), radius=radius, fill=SHADOW + (128,)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur)))

    panel = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle(box, radius=radius, fill=PARCHMENT + (alpha,))
    draw.rounded_rectangle(box, radius=radius, outline=accent + (255,), width=max(2, radius // 8))
    canvas.alpha_composite(panel)


def scrim(canvas: Image.Image, top: int, bottom: int, strength: int, invert: bool) -> None:
    """A vertical ink gradient, so a pale patch of art never swallows a plate."""

    height = max(1, bottom - top)
    gradient = Image.new("L", (1, height))
    gradient.putdata([round(strength * (i / height if invert else 1 - i / height)) for i in range(height)])
    band = Image.new("RGBA", (canvas.width, height), INK + (0,))
    band.putalpha(gradient.resize((canvas.width, height)))
    canvas.alpha_composite(band, (0, top))


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


def render_front(card: CardDef, art_path: Path, layout: Layout, fonts: Fonts) -> Image.Image:
    width, height = layout.size
    safe = layout.px(SAFE_IN)
    pad = layout.px(PLATE_PAD_IN)
    radius = layout.px(PLATE_RADIUS_IN)
    tracking = layout.px(TRACKING_IN)
    accent = accent_for(card)

    with Image.open(art_path) as art:
        canvas = cover(art.convert("RGB"), (width, height)).convert("RGBA")

    measure = ImageDraw.Draw(canvas)
    inner_width = width - 2 * safe - 2 * pad

    # --- Title plate: name, then the type line in tracked small caps --------
    name_font, name_lines = fit_title(
        measure, card.name, fonts, inner_width, layout.px(NAME_SIZE_IN), layout.px(NAME_MIN_SIZE_IN)
    )
    type_font = fonts.at("regular", layout.px(TYPE_SIZE_IN))
    name_leading = round(name_font.size * 1.14)
    title_height = pad + len(name_lines) * name_leading + round(type_font.size * 1.5) + pad
    title_box = (safe, safe, width - safe, safe + title_height)

    scrim(canvas, 0, title_box[3] + layout.px(0.22), 150, invert=False)
    plate(canvas, title_box, radius, accent)

    draw = ImageDraw.Draw(canvas)
    y = safe + pad
    for line in name_lines:
        draw.text(((width - draw.textlength(line, font=name_font)) / 2, y), line, font=name_font, fill=INK)
        y += name_leading
    type_text = card_text.type_line(card).upper()
    y += round(type_font.size * 0.18)
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

    scrim(canvas, body[1] - layout.px(0.28), height, 150, invert=True)
    plate(canvas, body, radius, accent)
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
    safe, pad = layout.px(SAFE_IN), layout.px(PLATE_PAD_IN)
    measure = ImageDraw.Draw(canvas)
    *_, plate_height = rules_block(card, layout, fonts, measure, width - 2 * safe - 2 * pad)
    return (safe, height - safe - plate_height, width - safe, height - safe)


def fill_rules_plate(canvas, card, box, layout, fonts, accent) -> None:
    draw = ImageDraw.Draw(canvas)
    safe, pad = layout.px(SAFE_IN), layout.px(PLATE_PAD_IN)
    inner_width = canvas.width - 2 * safe - 2 * pad
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
    safe, pad = layout.px(SAFE_IN), layout.px(PLATE_PAD_IN)
    row = layout.px(LABEL_SIZE_IN) + layout.px(VALUE_SIZE_IN) + layout.px(0.086)
    plate_height = pad + 2 * row - layout.px(0.034) + pad
    return (safe, height - safe - plate_height, width - safe, height - safe)


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
    """A text-only agenda card: parchment under an ink band, since no art exists.

    The band and its rule run off the edge rather than stopping short of it. A
    keyline set in from the trim advertises every millimetre the cutter wanders;
    one that bleeds off cannot be misaligned against anything.
    """

    width, height = layout.size
    safe, pad = layout.px(SAFE_IN), layout.px(PLATE_PAD_IN)
    inner_width = width - 2 * safe
    tracking = layout.px(TRACKING_IN)

    canvas = Image.new("RGB", (width, height), PARCHMENT)
    draw = ImageDraw.Draw(canvas)

    label_font = fonts.at("regular", layout.px(TYPE_SIZE_IN))
    name_font, name_lines = fit_title(
        draw, name, fonts, inner_width - 2 * pad, layout.px(NAME_SIZE_IN), layout.px(NAME_MIN_SIZE_IN)
    )
    name_leading = round(name_font.size * 1.16)
    band_height = safe + round(label_font.size * 2.1) + len(name_lines) * name_leading + layout.px(0.14)
    draw.rectangle((0, 0, width, band_height), fill=INK)
    rule = max(2, layout.px(0.010))
    draw.rectangle((0, band_height, width, band_height + rule), fill=GOLD)

    label = "AGENDA"
    y = safe + layout.px(0.04)
    draw_tracked(
        draw,
        ((width - tracked_width(draw, label, label_font, tracking)) / 2, y),
        label,
        label_font,
        GOLD,
        tracking,
    )
    y += round(label_font.size * 2.0)
    for line in name_lines:
        draw.text(((width - draw.textlength(line, font=name_font)) / 2, y), line, font=name_font, fill=PARCHMENT)
        y += name_leading

    # The win condition sits in the upper half of the parchment, where the eye
    # goes; the flavour line anchors the bottom.
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

    # Flavour is pinned to the bottom; the condition floats in what is left,
    # a little above centre so the card does not read as bottom-heavy.
    subtitle_y = height - safe - round(sub_font.size * 1.6)
    block = (
        len(lines) * body_leading
        + layout.px(0.30)
        + len(reminder_lines) * round(reminder_font.size * 1.28)
    )
    region_top = band_height + rule
    y = region_top + max(layout.px(0.22), round((subtitle_y - region_top - block) * 0.42))
    for line in lines:
        draw.text((safe + pad, y), line, font=body_font, fill=INK)
        y += body_leading

    y += layout.px(0.15)
    draw.line((safe + pad, y, width - safe - pad, y), fill=GOLD, width=max(1, layout.px(0.005)))
    y += layout.px(0.15)
    for line in reminder_lines:
        draw.text((safe + pad, y), line, font=reminder_font, fill=INK_SOFT)
        y += round(reminder_font.size * 1.28)

    draw.text(
        ((width - draw.textlength(subtitle, font=sub_font)) / 2, subtitle_y),
        subtitle,
        font=sub_font,
        fill=INK_SOFT,
    )
    return canvas


# --- Order file -------------------------------------------------------------
def build_xml(slots: list[tuple[Path, str]], cardback: Path, stock: str, foil: bool) -> str:
    """One `<card>` per slot, pointing at an absolute path on this machine.

    `sourceType` of `Local File` is what stops the desktop tool treating the
    path as a Google Drive id; the cardback tag has no room for a source type,
    but the tool infers one when the text is a path that exists.
    """

    order = ET.Element("order")
    details = ET.SubElement(order, "details")
    ET.SubElement(details, "quantity").text = str(len(slots))
    ET.SubElement(details, "stock").text = stock
    ET.SubElement(details, "foil").text = "true" if foil else "false"

    fronts = ET.SubElement(order, "fronts")
    for slot, (path, query) in enumerate(slots):
        card = ET.SubElement(fronts, "card")
        ET.SubElement(card, "id").text = str(path)
        ET.SubElement(card, "sourceType").text = "Local File"
        ET.SubElement(card, "slots").text = str(slot)
        ET.SubElement(card, "name").text = path.name
        ET.SubElement(card, "query").text = query
    ET.SubElement(order, "cardback").text = str(cardback)

    raw = ET.tostring(order, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="    ")


# --- CLI --------------------------------------------------------------------
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
        description="Compose card fronts from assets/ and write an MPC Autofill order.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "After running this, put the MPC Autofill `autofill` executable next to\n"
            "the generated .xml and run it. See docs/PRINTING.md."
        ),
    )
    parser.add_argument("--assets", type=Path, default=REPO_ROOT / "assets", help="where the art lives")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "build" / "mpc", help="output directory")
    parser.add_argument("--dpi", type=int, default=600, help="render resolution (default 600; MPC needs 300+)")
    parser.add_argument("--format", choices=("png", "jpg"), default="png", help="output image format")
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality when --format jpg")
    parser.add_argument(
        "--stock",
        default="(S30) Standard Smooth",
        help="MPC cardstock: (S27) Smooth, (S30) Standard Smooth, (S33) Superior Smooth, (M31) Linen, (P10) Plastic",
    )
    parser.add_argument("--foil", action="store_true", help="order foil fronts")
    parser.add_argument("--outmaneuver-copies", type=int, default=1, help="copies of Outmaneuver in the deck")
    parser.add_argument(
        "--include-agendas",
        action="store_true",
        help="append the 8 text-only agenda cards (no art exists for them)",
    )
    parser.add_argument("--only", help="comma-separated asset numbers to re-render, e.g. 26,41")
    parser.add_argument("--font-dir", action="append", default=[], help="extra directory to search for fonts")
    args = parser.parse_args(argv)

    if args.dpi < 300:
        parser.error(f"--dpi {args.dpi} is below MakePlayingCards' 300 DPI minimum")
    if args.dpi > MAX_USEFUL_DPI:
        print(f"note: the desktop tool downscales above {MAX_USEFUL_DPI} DPI, so {args.dpi} buys nothing")

    layout = Layout(args.dpi)
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

    cards_dir = args.out / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    only = {int(n) for n in args.only.split(",")} if args.only else None

    slots: list[tuple[Path, str]] = []
    alternates: list[str] = []
    for slot, (card, asset) in enumerate(zip(cards, chosen)):
        out_path = (cards_dir / f"{asset.index:02d} {card.name}").with_suffix(f".{args.format}")
        if only is None or asset.index in only:
            image = render_front(card, asset.path, layout, fonts)
            out_path = save(image, out_path, args.format, args.quality, args.dpi)
            print(f"  [{slot:>2}] {out_path.name}")
        if len(by_index[asset.index]) > 1:
            alternates.append(f"{asset.index:02d} {card.name} ({len(by_index[asset.index])} versions)")
        slots.append((out_path.resolve(), card.name.lower()))

    if args.include_agendas:
        for i, (name, subtitle, text) in enumerate(card_text.AGENDA_TEXT, start=85):
            out_path = (cards_dir / f"{i:02d} {name.replace(':', ' --')}").with_suffix(f".{args.format}")
            if only is None or i in only:
                out_path = save(
                    render_agenda(name, subtitle, text, layout, fonts),
                    out_path,
                    args.format,
                    args.quality,
                    args.dpi,
                )
                print(f"  [{len(slots):>2}] {out_path.name}")
            slots.append((out_path.resolve(), name.lower()))

    back_asset = by_index[0][0]
    back_path = (cards_dir / "00 Cardback").with_suffix(f".{args.format}")
    if only is None or 0 in only:
        with Image.open(back_asset.path) as art:
            back = cover(art.convert("RGB"), layout.size, top_bias=0.5)
            back_path = save(back, back_path, args.format, args.quality, args.dpi)

    xml_path = args.out / "succession.xml"
    xml_path.write_text(build_xml(slots, back_path.resolve(), args.stock, args.foil), encoding="utf-8")

    total_mb = sum(p.stat().st_size for p, _ in slots if p.exists()) / 1e6
    print(f"\n{len(slots)} fronts + 1 back at {args.dpi} DPI ({total_mb:.0f} MB) -> {cards_dir}")
    print(f"Order file -> {xml_path}")
    if alternates:
        print("\nCards with more than one version of the art (the lowest-numbered one was used):")
        for line in alternates:
            print(f"  {line}")
    print(
        "\nNext: put the MPC Autofill `autofill` executable in "
        f"{args.out}, run it, and pick succession.xml."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
