"""Run paid, synthetic OpenAI guide-page smokes without user data."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

from minerva_travel.page_generation import OpenAIGuidePageGenerator

SMOKE_DIR = Path("runtime/openai-page-smoke")
FIXTURE_PATH = SMOKE_DIR / "synthetic-family.png"
OUTPUT_PATH = SMOKE_DIR / "cover.png"
REVISION_OUTPUT_PATH = SMOKE_DIR / "cover-revision.png"
SUMMARY_OUTPUT_PATH = SMOKE_DIR / "summary.png"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--revision-instruction",
        help="Revise the existing synthetic cover with this design feedback.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate a summary using the synthetic photo and approved cover references.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixture = create_synthetic_family_fixture()
    generator = OpenAIGuidePageGenerator(quality="low")
    if args.summary:
        if not OUTPUT_PATH.is_file():
            raise SystemExit(f"Generate the base smoke cover first: {OUTPUT_PATH}")
        generator.generate_summary_page(
            family_photo=fixture,
            family_cover=OUTPUT_PATH,
            output_path=SUMMARY_OUTPUT_PATH,
            family_title="Família Aurora",
            trip_date="Julho de 2026",
            landmark_names=["Torre Eiffel", "Coliseu"],
            expected_visible_family_member_count=4,
        )
        _report_output(SUMMARY_OUTPUT_PATH)
        return
    reference = OUTPUT_PATH if args.revision_instruction else None
    output = REVISION_OUTPUT_PATH if reference else OUTPUT_PATH
    if reference is not None and not reference.is_file():
        raise SystemExit(f"Generate the base smoke cover first: {reference}")
    generator.generate_cover_page(
        family_photo=fixture,
        output_path=output,
        family_title="Família Aurora",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        expected_visible_family_member_count=4,
        revision_instruction=args.revision_instruction or "",
        reference_page=reference,
    )
    _report_output(output)
    if reference is not None and output.read_bytes() == reference.read_bytes():
        raise SystemExit("The revision returned bytes identical to the selected reference.")


def _report_output(output: Path) -> None:
    with Image.open(output) as image:
        digest = hashlib.sha256(output.read_bytes()).hexdigest()[:12]
        print(f"OpenAI smoke OK: {output} ({image.format}, {image.width}x{image.height}, {digest})")


if __name__ == "__main__":
    main()
