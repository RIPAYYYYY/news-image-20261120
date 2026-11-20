#!/usr/bin/env python3
"""THE DAILY WORLD - Friday, 20 November 2026 in one picture.

A single-file Python 3 program (standard library only) that draws a
newspaper front page for the make.fun bounty "news-image-20261120"
and writes it as a 1024x1024 PNG.

Everything on the page is drawn by hand in this file:

  * a 5x7 bitmap typeface, defined glyph by glyph below;
  * the rules, bands, skyline, missile trails and market chart are
    plain geometry on an in-memory framebuffer;
  * the PNG file is assembled chunk by chunk with zlib.

The program reads nothing, uses no clock and no randomness beyond a
fixed-seed generator, so two runs write byte-identical files.

The headlines are the world news of Friday 20 November 2026, as
reported that day (see README.md for the story list).
"""

import os
import struct
import zlib
from binascii import crc32

# ---------------------------------------------------------------- canvas

WIDTH = 1024
HEIGHT = 1024

PAPER = (247, 242, 231)      # warm newsprint
INK = (22, 19, 14)           # near-black ink
SOFT = (104, 97, 84)         # faded ink for furniture
RULE = (176, 168, 148)       # hairline grey
CRIMSON = (158, 30, 26)      # date-band red
NIGHT = (23, 26, 43)         # lead-panel sky
NIGHT2 = (58, 64, 98)        # skyline silhouette
GOLD = (216, 164, 44)        # lit windows / moon
WHITE = (250, 248, 242)

FB = bytearray(WIDTH * HEIGHT * 3)


def set_px(x, y, rgb):
    """Paint one pixel, clipping silently at the edges."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        i = (y * WIDTH + x) * 3
        FB[i] = rgb[0]
        FB[i + 1] = rgb[1]
        FB[i + 2] = rgb[2]


def fill_rect(x, y, w, h, rgb):
    for yy in range(y, y + h):
        if 0 <= yy < HEIGHT:
            base = yy * WIDTH
            for xx in range(x, x + w):
                if 0 <= xx < WIDTH:
                    i = (base + xx) * 3
                    FB[i] = rgb[0]
                    FB[i + 1] = rgb[1]
                    FB[i + 2] = rgb[2]


def hline(x, y, w, rgb, thick=1):
    fill_rect(x, y, w, thick, rgb)


def vline(x, y, h, rgb, thick=1):
    fill_rect(x, y, thick, h, rgb)


def draw_line(x0, y0, x1, y1, rgb, thick=1):
    """Bresenham line, optionally thickened by stamping squares."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        if thick <= 1:
            set_px(x, y, rgb)
        else:
            fill_rect(x - thick // 2, y - thick // 2, thick, thick, rgb)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def fill_circle(cx, cy, r, rgb):
    r2 = r * r
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r2:
                set_px(xx, yy, rgb)


def dotted_curve(x0, y0, cx, cy, x1, y1, rgb, steps=42, every=2):
    """A quadratic Bezier drawn as separated dots (a missile trail)."""
    for i in range(steps + 1):
        if i % every:
            continue
        t = i / steps
        u = 1.0 - t
        x = u * u * x0 + 2 * u * t * cx + t * t * x1
        y = u * u * y0 + 2 * u * t * cy + t * t * y1
        fill_rect(int(x) - 1, int(y) - 1, 3, 3, rgb)


def starburst(cx, cy, r, rgb):
    """Eight short rays around a centre: a distant explosion flash."""
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (1, -1), (-1, 1), (-1, -1)):
        draw_line(cx, cy, cx + dx * r, cy + dy * r, rgb, thick=2)
    fill_circle(cx, cy, 3, rgb)


class Lcg:
    """Tiny fixed-seed generator so the picture never changes."""

    def __init__(self, seed):
        self.state = seed & 0x7FFFFFFF

    def next(self, bound):
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state % bound


# ------------------------------------------------------------ PNG writer

def _chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", crc32(tag + payload) & 0xFFFFFFFF))


def encode_png():
    """Serialise the framebuffer as a truecolour PNG, filter 0 rows."""
    raw = bytearray()
    row_bytes = WIDTH * 3
    for y in range(HEIGHT):
        raw.append(0)
        start = y * row_bytes
        raw.extend(FB[start:start + row_bytes])
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


# ------------------------------------------------------------------ font
# A 5x7 bitmap face drawn for this page. Each glyph is seven rows of
# five characters; '#' is ink, '.' is paper. Only the characters the
# page actually uses are defined.

GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", ".#.#.", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#####", "...#.", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#..##", "#..##"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "/": ("....#", "...#.", "...#.", "..#..", "..#..", ".#...", "#...."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "£": (".##..", "#..#.", "#....", "####.", "#....", "#....", "#####"),
}

ADVANCE = 6  # glyph cell is 5 wide plus one column of tracking


def text_width(text, scale):
    if not text:
        return 0
    return len(text) * ADVANCE * scale - scale


def draw_text(x, y, text, scale, rgb):
    """Draw a single line of bitmap text with its top-left at (x, y)."""
    cx = x
    for ch in text:
        glyph = GLYPHS.get(ch)
        if glyph is None:
            glyph = GLYPHS["?"]
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, rgb)
        cx += ADVANCE * scale
    return cx


def draw_centered(y, text, scale, rgb, cx=WIDTH // 2):
    draw_text(cx - text_width(text, scale) // 2, y, text, scale, rgb)


def draw_right(x_right, y, text, scale, rgb):
    draw_text(x_right - text_width(text, scale), y, text, scale, rgb)


def wrap(text, scale, max_width):
    """Greedy word wrap: split text into lines that fit max_width."""
    lines = []
    current = ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_block(x, y, text, scale, rgb, max_width, leading):
    """Draw wrapped text; return the y just below the last line."""
    for line in wrap(text, scale, max_width):
        draw_text(x, y, line, scale, rgb)
        y += 7 * scale + leading
    return y


# ---------------------------------------------------------- illustrations

def draw_lead_panel(x, y, w, h):
    """Kyiv before dawn: skyline, moon, missile trails, two flashes."""
    rng = Lcg(20261120)
    # sky in horizontal bands, lighter towards the horizon
    band = h // 6
    for i in range(6):
        shade = (NIGHT[0] + i * 5, NIGHT[1] + i * 5, NIGHT[2] + i * 7)
        fill_rect(x, y + i * band, w, band + 1, shade)
    fill_circle(x + w - 58, y + 34, 15, GOLD)          # moon
    fill_circle(x + w - 66, y + 28, 13, NIGHT)         # moon shadow bite
    # skyline of uneven towers along the panel floor
    ground = y + h - 22
    bx = x + 6
    while bx < x + w - 16:
        bw = 16 + rng.next(20)
        bh = 26 + rng.next(52)
        fill_rect(bx, ground - bh, bw, bh, NIGHT2)
        for _ in range(bw // 6):
            wx = bx + 2 + rng.next(bw - 5)
            wy = ground - bh + 3 + rng.next(bh - 8)
            if rng.next(3):
                set_px(wx, wy, GOLD)
                set_px(wx + 1, wy, GOLD)
        bx += bw + 2 + rng.next(5)
    fill_rect(x, ground, w, 3, NIGHT2)
    # two dotted trails arcing in, ending in flashes over the towers
    dotted_curve(x + 36, y + 10, x + 120, y + 52, x + 168, ground - 34,
                 GOLD)
    dotted_curve(x + w - 30, y + 6, x + w - 130, y + 60, x + w - 96,
                 ground - 44, WHITE)
    starburst(x + 168, ground - 34, 10, GOLD)
    starburst(x + w - 96, ground - 44, 8, GOLD)
    # caption strip
    fill_rect(x, y + h - 20, w, 20, NIGHT)
    draw_text(x + 10, y + h - 14, "KYIV BEFORE DAWN - DRAWN BY OUR ARTIST",
              1, WHITE)


def draw_downtrend(x, y):
    """A little red falling line for the markets column."""
    pts = [(0, 0), (16, 4), (30, 3), (48, 9), (64, 8), (84, 14)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        draw_line(x + ax, y + ay, x + bx, y + by, CRIMSON, thick=2)
    ex, ey = x + pts[-1][0], y + pts[-1][1]
    draw_line(ex, ey, ex - 7, ey - 1, CRIMSON, thick=2)
    draw_line(ex, ey, ex - 1, ey - 7, CRIMSON, thick=2)


# ------------------------------------------------------------ the stories
# The news of Friday 20 November 2026, as reported that day:
#  - CNN/Reuters wires, 20 Nov: Russia's overnight missile and drone
#    strike on Kyiv hours after the Shenzhen trilateral summit.
#  - Reuters, 20 Nov: Houthi claims on Saudi targets, Hormuz tanker
#    fire, Brent crude edging up to $92.22.
#  - AP via Toronto Star / News Media House, 20 Nov: COP31 in Antalya
#    enters its final day; Africa seeks tripled climate finance.
#  - News Media House, 20 Nov: Asian markets plunge on AI bubble
#    fears despite Anthropic's record IPO; Seoul fell 4.2% (Reuters).

LEAD_KICKER = "UKRAINE WAR - THE MORNING AFTER THE SUMMIT"
LEAD_HEAD = "RUSSIA POUNDS KYIV HOURS AFTER 'PEACE' SUMMIT"
LEAD_BODY = (
    "HOURS AFTER PRESIDENTS TRUMP, XI AND PUTIN ISSUED A PEACE "
    "DECLARATION IN SHENZHEN, RUSSIAN BALLISTIC MISSILES AND DRONES "
    "STRUCK KYIV FOR MORE THAN SIX HOURS OVERNIGHT. AT LEAST FIVE "
    "PEOPLE WERE KILLED - THREE IN THE CAPITAL, TWO IN LVIV - AND "
    "THREE BRIDGES OVER THE DNIPRO WERE DAMAGED. RESIDENTS SHELTERED "
    "IN METRO STATIONS."
)

COLUMNS = [
    ("MIDDLE EAST",
     "HOUTHIS CLAIM STRIKES ON SAUDI TARGETS",
     "YEMEN'S HOUTHIS SAID THEY STRUCK FOUR TARGETS IN SAUDI ARABIA. "
     "RIYADH SAID ITS AIR DEFENCES DOWNED TWO DRONES, A TANKER CAUGHT "
     "FIRE AFTER HITTING A MINE NEAR HORMUZ, AND BRENT CRUDE EDGED "
     "UP TO $92.22."),
    ("CLIMATE",
     "COP31 FINAL DAY: FINANCE FIGHT OPEN",
     "THE UN SUMMIT IN ANTALYA BEGAN ITS FINAL DAY WITH THE BIG "
     "QUESTIONS OPEN. AFRICA PRESSED TO TRIPLE CLIMATE FINANCE, "
     "EUROPE URGED A FOCUS ON PLEDGES ALREADY MADE, AND FOSSIL-FUEL "
     "CUTS WERE STILL CONTESTED."),
    ("MARKETS",
     "ASIAN MARKETS SINK AS AI FEARS GROW",
     "SHARES SLID ACROSS ASIA DESPITE ANTHROPIC'S RECORD-BREAKING "
     "MARKET DEBUT, AS INVESTORS ASKED HOW LONG THE AI BOOM CAN "
     "RUN. SEOUL FELL 4.2%; WALL STREET HAD SHED 2% TO SEVEN-MONTH "
     "LOWS."),
]

BRIEFS = [
    "INDONESIA: PRABOWO AND XI DISCUSS SOUTH CHINA SEA COOPERATION",
    "BRITAIN PLEDGES 1,000 DRONES FOR UKRAINE IN £260M PACKAGE",
    "TAIWAN FLAGS 2,700 CHINA-LINKED ACCOUNTS TO META",
    "SEOUL COURT UPHOLDS ACQUITTAL OF KAKAO FOUNDER KIM BEOM-SU",
    "MAGNITUDE 5.6 EARTHQUAKE STRIKES NEAR NEW CALEDONIA",
    "TOKYO: 13,000 MARCH AGAINST PM TAKAICHI'S GOVERNMENT",
]


# ------------------------------------------------------------------ page

def build_page():
    fill_rect(0, 0, WIDTH, HEIGHT, PAPER)
    left = 48
    right = WIDTH - 48

    # furniture line and masthead
    draw_text(left, 26, "VOL. I - NO. 4", 2, SOFT)
    draw_centered(26, "THE WORLD IN ONE PICTURE", 2, SOFT)
    draw_right(right, 26, "FRIDAY EDITION", 2, SOFT)
    hline(left, 52, right - left, INK, 3)
    hline(left, 58, right - left, INK, 1)
    draw_centered(68, "THE DAILY WORLD", 9, INK)
    hline(left, 140, right - left, INK, 1)
    hline(left, 145, right - left, INK, 3)

    # crimson date band
    fill_rect(left, 156, right - left, 46, CRIMSON)
    draw_centered(165, "FRIDAY, 20 NOVEMBER 2026", 4, WHITE)

    # lead story
    draw_text(left, 218, LEAD_KICKER, 2, CRIMSON)
    draw_right(right, 218, "LEAD STORY", 2, SOFT)
    y = draw_block(left, 240, LEAD_HEAD, 6, INK, right - left, 6)
    draw_lead_panel(left, y + 12, 404, 168)
    draw_block(left + 428, y + 12, LEAD_BODY, 2, INK, right - left - 428, 3)
    y += 12 + 168 + 18
    hline(left, y, right - left, RULE, 2)

    # three story columns
    y += 14
    col_w = (right - left - 40) // 3
    for i, (kicker, head, body) in enumerate(COLUMNS):
        cx = left + i * (col_w + 20)
        draw_text(cx, y, kicker, 2, CRIMSON)
        if kicker == "MARKETS":
            draw_downtrend(cx + col_w - 92, y + 1)
        hy = draw_block(cx, y + 22, head, 3, INK, col_w, 4)
        draw_block(cx, hy + 6, body, 2, INK, col_w, 2)
    y += 268
    hline(left, y, right - left, RULE, 2)

    # briefs, two columns of three
    y += 14
    draw_text(left, y, "AROUND THE WORLD IN BRIEF", 2, CRIMSON)
    y += 24
    half = (right - left - 24) // 2
    for i, brief in enumerate(BRIEFS):
        bx = left + (i // 3) * (half + 24)
        by = y + (i % 3) * 44
        fill_rect(bx, by + 3, 8, 8, CRIMSON)
        draw_block(bx + 22, by, brief, 2, INK, half - 22, 2)

    # footer
    fy = HEIGHT - 46
    hline(left, fy, right - left, INK, 2)
    draw_centered(fy + 12,
                  "SET IN A HAND-DRAWN BITMAP FACE - DRAWN BY A PYTHON "
                  "PROGRAM, NO PHOTOGRAPHS", 2, SOFT)


def main():
    build_page()
    data = encode_png()

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    primary = os.path.join(out_dir, "entry.png")
    beside = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "entry.png")

    # The output directory is where the PNG has to land; create it if the
    # host has not, but a failure here must not stop us before we try.
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError:
        pass

    # Write the primary target first, then the copy beside this script as a
    # best-effort extra. Each write stands on its own: a target that cannot
    # be opened (e.g. a read-only script directory) is skipped, never fatal,
    # as long as at least one copy of the page made it to disk.
    written = []
    for path in dict.fromkeys((primary, beside)):
        try:
            with open(path, "wb") as fh:
                fh.write(data)
        except OSError:
            continue
        written.append(path)

    if not written:
        raise SystemExit("entry.png could not be written anywhere")
    print("wrote", len(data), "bytes to", ", ".join(written))


if __name__ == "__main__":
    main()
