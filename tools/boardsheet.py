"""The board as something you can print at home and cut out.

The seat cards ride along in the MPC order for free, so anyone printing a deck
already has the board. This is for the playtester who is not ordering anything:
the same seven cards, at true size, laid out on A4 or Letter with cut guides.

True size is the constraint that drives the layout. A seat card has to sit
alongside the courtier cards it receives, so it cannot be scaled to fit the
paper -- the paper has to be paginated to fit the cards. At 2.48 x 3.46 in
that is six to a page either way, but not the same six: A4 is the narrower
sheet and takes two across and three down, Letter the shorter one and takes
three across and two down. Seven cards therefore run to two pages on both,
split four and three.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

#: Portrait, in inches. A4 is the taller and narrower of the two.
PAPERS: dict[str, tuple[float, float]] = {
    "a4": (8.27, 11.69),
    "letter": (8.50, 11.00),
}

#: Consumer printers cannot reach the edge; 0.4 in clears every one we know of.
MARGIN_IN = 0.40
#: Between cards, enough to get scissors in without wasting a row.
GUTTER_IN = 0.12
#: How far the corner guides sit outside each card, and how long they run.
MARK_OFFSET_IN = 0.035
MARK_LENGTH_IN = 0.16

INK = (17, 36, 60)
GUIDE = (150, 150, 150)


@dataclass(frozen=True)
class Sheet:
    """One rendition of the board, for one paper size."""

    paper: str
    dpi: int

    @property
    def size(self) -> tuple[int, int]:
        width, height = PAPERS[self.paper]
        return round(width * self.dpi), round(height * self.dpi)

    def px(self, inches: float) -> int:
        return round(inches * self.dpi)


def grid(sheet: Sheet, card: tuple[int, int]) -> tuple[int, int]:
    """How many cards fit across and down, at true size.

    Returns at least one of each even when the card is too big for the paper,
    so a caller gets a page with one card running off it rather than a divide
    by zero -- and sees the problem immediately.
    """

    page_w, page_h = sheet.size
    card_w, card_h = card
    gutter = sheet.px(GUTTER_IN)
    usable_w = page_w - 2 * sheet.px(MARGIN_IN) + gutter
    usable_h = page_h - 2 * sheet.px(MARGIN_IN) + gutter
    return (
        max(1, usable_w // (card_w + gutter)),
        max(1, usable_h // (card_h + gutter)),
    )


def cut_marks(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], sheet: Sheet) -> None:
    """Four corner brackets, outside the card, so the blade has a line to follow.

    Marks rather than a full rectangle: a drawn border would be cut through and
    leave a grey edge on the card, where corner guides are cut away entirely.
    """

    x0, y0, x1, y1 = box
    off, length = sheet.px(MARK_OFFSET_IN), sheet.px(MARK_LENGTH_IN)
    width = max(1, sheet.px(0.004))
    for x, dx in ((x0, -1), (x1, 1)):
        for y, dy in ((y0, -1), (y1, 1)):
            draw.line((x + dx * off, y + dy * off, x + dx * (off + length), y + dy * off), fill=GUIDE, width=width)
            draw.line((x + dx * off, y + dy * off, x + dx * off, y + dy * (off + length)), fill=GUIDE, width=width)


def _caption_font(sheet: Sheet, fonts) -> ImageFont.FreeTypeFont:
    return fonts.at("regular", sheet.px(0.11))


def build_pages(cards: list[Image.Image], sheet: Sheet, fonts, title: str) -> list[Image.Image]:
    """Lay the cards out at true size across as many pages as they need."""

    if not cards:
        return []
    card_w, card_h = cards[0].size
    across, down = grid(sheet, (card_w, card_h))
    per_page = across * down

    page_w, _ = sheet.size
    gutter = sheet.px(GUTTER_IN)
    block_w = across * card_w + (across - 1) * gutter
    left = (page_w - block_w) // 2

    # Spread evenly rather than filling each page in turn: seven cards over two
    # pages is 4 and 3, not 6 and a lonely one. Same paper, better to cut.
    page_count = -(-len(cards) // per_page)
    base, extra = divmod(len(cards), page_count)
    chunks: list[list[Image.Image]] = []
    cut = 0
    for index in range(page_count):
        take = base + (1 if index < extra else 0)
        chunks.append(cards[cut : cut + take])
        cut += take

    pages: list[Image.Image] = []
    for start, chunk in enumerate(chunks):
        page = Image.new("RGB", sheet.size, (255, 255, 255))
        draw = ImageDraw.Draw(page)

        font = _caption_font(sheet, fonts)
        caption = title if start == 0 else f"{title} (continued)"
        draw.text((left, sheet.px(MARGIN_IN) - round(font.size * 1.6)), caption, font=font, fill=INK)

        # Top-aligned, not centred: a page holding fewer rows than it could
        # would otherwise float its cards away from the caption above them.
        top = sheet.px(MARGIN_IN)

        for i, card in enumerate(chunk):
            column, row = i % across, i // across
            x = left + column * (card_w + gutter)
            y = top + row * (card_h + gutter)
            page.paste(card, (x, y))
            cut_marks(draw, (x, y, x + card_w, y + card_h), sheet)
        pages.append(page)
    return pages


def write(path: Path, cards: list[Image.Image], paper: str, dpi: int, fonts, title: str) -> Path:
    """Save the sheet as a PDF that prints at true size.

    `resolution` is what makes that true: without it the reader has no idea how
    many pixels make an inch, and a card comes out whatever size the printer
    guesses.
    """

    sheet = Sheet(paper, dpi)
    pages = build_pages(cards, sheet, fonts, title)
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        path,
        "PDF",
        resolution=dpi,
        save_all=True,
        append_images=pages[1:],
    )
    return path
