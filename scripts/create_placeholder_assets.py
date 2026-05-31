import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image, ImageDraw, ImageFont

from minerva_travel.catalog import load_catalog


def main() -> None:
    catalog = load_catalog()
    for destination in catalog.destinations:
        for landmark in destination.landmarks:
            create_landmark_image(landmark.image, landmark.name, destination.city, lineart=False)
            create_landmark_image(
                landmark.lineart_image,
                landmark.name,
                destination.city,
                lineart=True,
            )


def create_landmark_image(path: Path, name: str, city: str, lineart: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    background = "#ffffff" if lineart else "#f6ead7"
    image = Image.new("RGB", (1200, 850), background)
    draw = ImageDraw.Draw(image)
    font_title = _font(58)
    font_city = _font(38)
    ink = "#111111" if lineart else "#315f7d"
    fill = "#ffffff" if lineart else "#d8ebf1"

    draw.rounded_rectangle((70, 70, 1130, 780), radius=30, fill=fill, outline=ink, width=5)
    draw.polygon(
        [(600, 160), (330, 620), (870, 620)],
        outline=ink,
        fill=None if lineart else "#c9d8bd",
        width=8,
    )
    draw.rectangle((430, 620, 770, 720), outline=ink, fill=None if lineart else "#c7a77c", width=8)
    draw.text((600, 390), name, anchor="mm", fill=ink, font=font_title)
    draw.text((600, 465), city, anchor="mm", fill=ink, font=font_city)
    image.save(path)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


if __name__ == "__main__":
    main()
