"""A courtier's sigil, drawn for the printed card.

The same mark the browser game draws (web/src/components/Sigil.tsx), in the
same 40-unit square, so the game can lay its live sigil exactly over the
printed one:

    faith  -> the shape    One God a circle, Old Gods a square, Mystery Cults
                           a hexagon; godless a diamond
    house  -> its colour   Argaian red, Mitreas green, Amonides blue; no
                           house black
    estate -> the glyph    Military a sword, Merchant a coin, Church praying
                           hands; Commons nothing
    origin -> the border   Imperial gold, Barbarian iron

`draw_sigil` paints it anti-aliased (drawn large, then scaled down) onto a
card; `SIGIL_*_IN` say where it sits, and the game's CSS mirrors them.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

# Keep in step with web/src/components/Sigil.tsx.
HOUSE_COLOUR = {
    "Argaian": (200, 69, 58),
    "Mitreas": (63, 154, 85),
    "Amonides": (61, 111, 196),
    "None": (21, 23, 28),
}
ORIGIN_COLOUR = {
    "Imperial": (240, 200, 101),
    "Barbarian": (174, 184, 196),
}
GLYPH_INK = (245, 236, 216)
EDGE = (0, 0, 0, 166)

#: Where the sigil sits on the printed card, in inches from the trimmed
#: card's top-left corner, and how wide it is: the art's lower left, just
#: clear of the attribute plate. The game's CSS (`.card .face .sigil`) places
#: its live sigil by the same numbers, as percentages of the trimmed card.
SIGIL_SIZE_IN = 0.44
SIGIL_CENTRE_X_IN = 0.43
SIGIL_CENTRE_Y_IN = 2.46

HEX = [(20, 2.5), (35.2, 11.25), (35.2, 28.75), (20, 37.5), (4.8, 28.75), (4.8, 11.25)]
DIAMOND = [(20, 1.5), (38.5, 20), (20, 38.5), (1.5, 20)]


def _cubic(p0, p1, p2, p3, steps=12):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        out.append(
            (
                u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
            )
        )
    return out


# Two palms pressed together: the web glyph's path, with its curves sampled.
HANDS = (
    [(20, 6.5)]
    + _cubic((20, 6.5), (17.2, 9.2), (14.8, 13.4), (14.3, 18.5))
    + [(13.8, 23.2), (12.2, 25.8), (12.2, 31.5), (27.8, 31.5), (27.8, 25.8), (26.2, 23.2), (25.7, 18.5)]
    + _cubic((25.7, 18.5), (25.2, 13.4), (22.8, 9.2), (20, 6.5))
)


#: Centre to edge of each shape, so it can be grown or shrunk by a width
#: (an SVG stroke is centred on the edge; here each band is its own fill).
APOTHEM = {"The One God": 16.5, "Old Gods": 15.5, "Mystery Cults": 15.2}
DIAMOND_APOTHEM = 18.5 / 2**0.5


def _shape(draw: ImageDraw.ImageDraw, faith: str, s: float, grow: float, fill) -> None:
    """The faith's shape in a 40-unit square scaled by `s`, its edge moved out
    by `grow` units (in by a negative one)."""

    if faith == "The One God":
        r = 16.5 + grow
        draw.ellipse(((20 - r) * s, (20 - r) * s, (20 + r) * s, (20 + r) * s), fill=fill)
    elif faith == "Old Gods":
        h = 15.5 + grow
        draw.rounded_rectangle(((20 - h) * s, (20 - h) * s, (20 + h) * s, (20 + h) * s), radius=max(0, 3 + grow) * s, fill=fill)
    else:
        points, apothem = (HEX, APOTHEM["Mystery Cults"]) if faith == "Mystery Cults" else (DIAMOND, DIAMOND_APOTHEM)
        k = (apothem + grow) / apothem
        draw.polygon([((20 + (x - 20) * k) * s, (20 + (y - 20) * k) * s) for x, y in points], fill=fill)


def _glyph(draw: ImageDraw.ImageDraw, estate: str, ground, s: float) -> None:
    def box(x0, y0, x1, y1):
        return (x0 * s, y0 * s, x1 * s, y1 * s)

    if estate == "Military":
        draw.polygon([(20 * s, 7.5 * s), (22.6 * s, 11.5 * s), (22.6 * s, 24 * s), (17.4 * s, 24 * s), (17.4 * s, 11.5 * s)], fill=GLYPH_INK)
        draw.rounded_rectangle(box(13, 24, 27, 26.8), radius=1 * s, fill=GLYPH_INK)
        draw.rectangle(box(18.7, 26.8, 21.3, 31.4), fill=GLYPH_INK)
        draw.ellipse(box(18, 30.6, 22, 34.6), fill=GLYPH_INK)
    elif estate == "Merchant":
        draw.ellipse(box(11, 11, 29, 29), fill=GLYPH_INK)
        draw.ellipse(box(13.8, 13.8, 26.2, 26.2), outline=ground, width=max(1, round(1.4 * s)))
        draw.rectangle(box(18.2, 18.2, 21.8, 21.8), fill=ground)
    elif estate == "Church":
        draw.polygon([(x * s, y * s) for x, y in HANDS], fill=GLYPH_INK)
        line = max(1, round(1.5 * s))
        draw.line(box(20, 9.5, 20, 31.5), fill=ground, width=line)
        draw.line(box(12.2, 26.4, 27.8, 26.4), fill=ground, width=line)
    # Commons: nothing


def sigil_image(estate: str, faith: str, family: str, origin: str, size_px: int) -> Image.Image:
    """The sigil alone, `size_px` square, on a transparent ground."""

    scale = 4  # drawn large, then scaled down: Pillow's shapes are not anti-aliased
    big = size_px * scale
    s = big / 40
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = HOUSE_COLOUR.get(family, HOUSE_COLOUR["None"])
    ring = ORIGIN_COLOUR.get(origin, ORIGIN_COLOUR["Imperial"])
    # A dark edge first, so the mark stands off any painting; then the shape,
    # its border, and the sign inside.
    _shape(draw, faith, s, 3.25, EDGE)
    _shape(draw, faith, s, 1.6, ring + (255,))
    _shape(draw, faith, s, -1.6, fill + (255,))
    _glyph(draw, estate, fill, s)
    return image.resize((size_px, size_px), Image.LANCZOS)


def draw_sigil(canvas: Image.Image, estate: str, faith: str, family: str, origin: str, centre, size_px: int) -> None:
    """Paint the sigil onto `canvas` (RGBA), centred on `centre`."""

    mark = sigil_image(estate, faith, family, origin, size_px)
    x = round(centre[0] - size_px / 2)
    y = round(centre[1] - size_px / 2)
    canvas.alpha_composite(mark, (x, y))
