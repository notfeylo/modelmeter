"""Render the Tallybeam mark as a Windows application icon."""
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
scale = SIZE / 64
image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=round(18 * scale), fill="#122734")
for x, top in ((15, 28), (25, 20), (35, 30), (45, 16)):
    draw.line(((x * scale, top * scale), (x * scale, 43 * scale)), fill="#A8E6D0", width=round(5 * scale))
draw.line(((12 * scale, 49 * scale), (51 * scale, 11 * scale)), fill="#F2B36F", width=round(4 * scale))

icon = image.resize((256, 256), Image.Resampling.LANCZOS)
(ROOT / "assets").mkdir(exist_ok=True)
icon.save(ROOT / "assets" / "tallybeam.ico", format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
