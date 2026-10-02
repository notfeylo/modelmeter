"""Render the Modelmeter Activity beams mark as a Windows application icon."""
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
scale = SIZE / 256
image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=round(62 * scale), fill="#303236")


def rounded_line(points, color, width):
    coords = [(round(x * scale), round(y * scale)) for x, y in points]
    radius = round(width * scale / 2)
    draw.line(coords, fill=color, width=round(width * scale), joint="curve")
    for x, y in (coords[0], coords[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


rounded_line([(51, 181), (51, 76), (89, 131), (128, 76), (128, 181)], "#F5F6F8", 17)
for x, top, color in ((155, 130, "#9385F8"), (184, 100, "#79AFDF"), (213, 69, "#55DCC7")):
    rounded_line([(x, 176), (x, top)], color, 18)
rounded_line([(151, 193), (219, 193)], "#666B74", 5)

icon = image.resize((256, 256), Image.Resampling.LANCZOS)
(ROOT / "assets").mkdir(exist_ok=True)
icon.save(ROOT / "assets" / "tallybeam.ico", format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
