"""Run one paid, synthetic OpenAI cover-page smoke without user data."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from minerva_travel.page_generation import OpenAIGuidePageGenerator

SMOKE_DIR = Path("runtime/openai-page-smoke")
FIXTURE_PATH = SMOKE_DIR / "synthetic-family.png"
OUTPUT_PATH = SMOKE_DIR / "cover.png"


def create_synthetic_family_fixture() -> Path:
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1024, 1024), "#c9e8f2")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 610, 1024, 1024), fill="#8fcf91")
    draw.ellipse((740, 80, 900, 240), fill="#ffd36b")
    for x, height, shirt, hair in (
        (160, 420, "#f06a50", "#58361f"),
        (360, 480, "#496f9d", "#31261e"),
        (590, 350, "#f0b94d", "#8b582b"),
        (770, 320, "#8c6ab1", "#4a3025"),
    ):
        head_y = 600 - height
        draw.ellipse((x, head_y, x + 130, head_y + 130), fill="#e8b58d")
        draw.pieslice((x - 5, head_y - 15, x + 135, head_y + 105), 180, 360, fill=hair)
        draw.rounded_rectangle(
            (x - 25, head_y + 115, x + 155, 860),
            radius=55,
            fill=shirt,
        )
        draw.ellipse((x + 35, head_y + 52, x + 46, head_y + 63), fill="#252525")
        draw.ellipse((x + 84, head_y + 52, x + 95, head_y + 63), fill="#252525")
        draw.arc((x + 42, head_y + 62, x + 91, head_y + 100), 10, 170, fill="#813b36", width=4)
    image.save(FIXTURE_PATH, format="PNG")
    return FIXTURE_PATH


def main() -> None:
    fixture = create_synthetic_family_fixture()
    generator = OpenAIGuidePageGenerator(quality="low")
    generator.generate_cover_page(
        family_photo=fixture,
        output_path=OUTPUT_PATH,
        family_title="Família Aurora",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        expected_visible_family_member_count=4,
    )
    with Image.open(OUTPUT_PATH) as image:
        print(f"OpenAI smoke OK: {OUTPUT_PATH} ({image.format}, {image.width}x{image.height})")


if __name__ == "__main__":
    main()
