"""The whole game as sheets you can print at home and cut out.

For the playtester who is not ordering a deck: every card at true size,
nine to a page on A4 or Letter, then a page of backs. `mpcfill.py --profile
sheets` builds it, with the rulebook (tools/rulebook.py) in front, as one PDF
per paper size.

Nine to a page only fits if the cards touch. Three cards across are 7.44 in
and three down 10.38 in, and Letter is 11 in tall, so a gutter between them
would push the last row off. Touching cards share a cut line, which is fewer
cuts anyway, and each card's own border is what you are cutting along. The
guides sit in the margin, outside the block, at every line the blade runs.

The backs page is the same grid. The cards are centred on the page, so it
lines up on the reverse of any sheet whichever way it is flipped; a printer
that cannot print both sides can skip it, and a card sleeved in front of an
ordinary playing card hides its face just as well.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from tools.boardsheet import GUIDE, INK, Sheet

ACROSS, DOWN = 3, 3
#: Above the block, room for one line saying what the page is.
CAPTION_IN = 0.12
#: How far a guide runs into the margin, and how far it stops short of the card.
GUIDE_LENGTH_IN = 0.18
GUIDE_GAP_IN = 0.04


class Cards:
    """Card images held as JPEG, not pixels: 94 cards at 300 DPI is 200 MB raw."""

    def __init__(self) -> None:
        self._held: list[bytes] = []
        self.size: tuple[int, int] | None = None

    def add(self, image: Image.Image) -> None:
        self.size = self.size or image.size
        buffer = BytesIO()
        image.convert("RGB").save(buffer, "JPEG", quality=90)
        self._held.append(buffer.getvalue())

    def __len__(self) -> int:
        return len(self._held)

    def __iter__(self):
        for data in self._held:
            yield Image.open(BytesIO(data))


def origin(sheet: Sheet, card: tuple[int, int]) -> tuple[int, int]:
    """Where the top-left card goes: the block of nine centred on the page."""

    page_w, page_h = sheet.size
    return (page_w - ACROSS * card[0]) // 2, (page_h - DOWN * card[1]) // 2


def guides(draw: ImageDraw.ImageDraw, sheet: Sheet, card: tuple[int, int]) -> None:
    """A short line in the margin at every edge the blade follows."""

    left, top = origin(sheet, card)
    right, bottom = left + ACROSS * card[0], top + DOWN * card[1]
    gap, length = sheet.px(GUIDE_GAP_IN), sheet.px(GUIDE_LENGTH_IN)
    width = max(1, sheet.px(0.006))
    for column in range(ACROSS + 1):
        x = left + column * card[0]
        draw.line((x, top - gap - length, x, top - gap), fill=GUIDE, width=width)
        draw.line((x, bottom + gap, x, bottom + gap + length), fill=GUIDE, width=width)
    for row in range(DOWN + 1):
        y = top + row * card[1]
        draw.line((left - gap - length, y, left - gap, y), fill=GUIDE, width=width)
        draw.line((right + gap, y, right + gap + length, y), fill=GUIDE, width=width)


def _page(sheet: Sheet, card: tuple[int, int], images, caption: str, fonts) -> Image.Image:
    page = Image.new("RGB", sheet.size, (255, 255, 255))
    draw = ImageDraw.Draw(page)
    left, top = origin(sheet, card)
    for i, image in enumerate(images):
        page.paste(image, (left + (i % ACROSS) * card[0], top + (i // ACROSS) * card[1]))
    guides(draw, sheet, card)
    # Over the top guides, on a white ground: Letter leaves a third of an inch
    # above the block, not room for both, and the guides below the block mark
    # the same lines.
    font = fonts.at("regular", sheet.px(CAPTION_IN))
    y = max(sheet.px(0.1), top - sheet.px(GUIDE_GAP_IN) - round(font.size * 1.5))
    box = draw.textbbox((left, y), caption, font=font)
    pad = sheet.px(0.03)
    draw.rectangle((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), fill=(255, 255, 255))
    draw.text((left, y), caption, font=font, fill=INK)
    return page


def pages(cards: Cards, back: Image.Image, paper: str, dpi: int, fonts) -> list[Image.Image]:
    """The card pages, nine to a page, then one page of backs."""

    sheet = Sheet(paper, dpi)
    card = cards.size
    assert card is not None, "no cards to lay out"
    per_page = ACROSS * DOWN
    total = -(-len(cards) // per_page)
    out: list[Image.Image] = []
    batch: list[Image.Image] = []

    def flush() -> None:
        caption = (
            f"Court of Succession — cards, sheet {len(out) + 1} of {total}. "
            "Print at actual size (100%) and cut on the lines."
        )
        out.append(_page(sheet, card, batch, caption, fonts))
        batch.clear()

    for image in cards:
        batch.append(image)
        if len(batch) == per_page:
            flush()
    if batch:
        flush()
    out.append(
        _page(
            sheet,
            card,
            [back.resize(card)] * per_page,
            "Card backs: print on the back of every sheet, or sleeve each card in front of a playing card.",
            fonts,
        )
    )
    return out


def write(path: Path, front_matter: list[Image.Image], body: list[Image.Image], dpi: int) -> Path:
    """One PDF, front matter first, at a resolution that prints at true size."""

    everything = front_matter + body
    path.parent.mkdir(parents=True, exist_ok=True)
    everything[0].save(path, "PDF", resolution=dpi, save_all=True, append_images=everything[1:])
    return path
