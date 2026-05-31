from pathlib import Path
from time import sleep
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont


class ImageGenerator(Protocol):
    def generate_cover(
        self,
        family_photo: Path,
        output_path: Path,
        title: str,
        destination_names: list[str],
    ) -> Path:
        """Generate a cover image and return its local path."""

    def generate_landmark_image(
        self,
        landmark_name: str,
        city: str,
        country: str,
        output_path: Path,
    ) -> Path:
        """Generate an image for a tourist landmark and return its local path."""


class PlaceholderImageGenerator:
    def generate_cover(
        self,
        family_photo: Path,
        output_path: Path,
        title: str,
        destination_names: list[str],
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (1200, 1600), "#f7efe3")
        draw = ImageDraw.Draw(image)
        font_large = _font(74)
        font_medium = _font(42)
        font_small = _font(32)

        draw.rounded_rectangle(
            (90, 90, 1110, 1510),
            radius=36,
            fill="#fffaf1",
            outline="#6a93b8",
            width=6,
        )
        draw.ellipse((170, 245, 1030, 1025), fill="#d8ebf1", outline="#89abc2", width=5)
        draw.rectangle((305, 760, 895, 1040), fill="#c9b59b", outline="#7d6549", width=5)

        people_x = [430, 545, 665, 780]
        colors = ["#6a93b8", "#d77a61", "#83a95c", "#c9a94d"]
        for index, x in enumerate(people_x):
            draw.ellipse((x - 42, 585, x + 42, 669), fill="#f2c6a0", outline="#7d6549", width=3)
            draw.rounded_rectangle(
                (x - 52, 670, x + 52, 860),
                radius=28,
                fill=colors[index],
                outline="#7d6549",
                width=3,
            )

        draw.text((600, 1120), "CAPA PLACEHOLDER", anchor="mm", fill="#214c70", font=font_large)
        draw.text((600, 1205), title, anchor="mm", fill="#214c70", font=font_medium)
        draw.text(
            (600, 1270),
            " + ".join(destination_names),
            anchor="mm",
            fill="#5a6f7c",
            font=font_small,
        )
        draw.text(
            (600, 1365),
            f"Foto base: {family_photo.name}",
            anchor="mm",
            fill="#7d6549",
            font=font_small,
        )
        image.save(output_path)
        return output_path

    def generate_landmark_image(
        self,
        landmark_name: str,
        city: str,
        country: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (1200, 850), "#f7efe3")
        draw = ImageDraw.Draw(image)
        font_large = _font(58)
        font_medium = _font(34)

        draw.rounded_rectangle(
            (70, 70, 1130, 780),
            radius=36,
            fill="#d8ebf1",
            outline="#6a93b8",
            width=6,
        )
        draw.ellipse((160, 125, 1040, 720), fill="#fff7df", outline="#d77a61", width=4)
        draw.text(
            (600, 375),
            landmark_name,
            anchor="mm",
            fill="#214c70",
            font=font_large,
        )
        draw.text(
            (600, 455),
            f"{city}, {country}",
            anchor="mm",
            fill="#7d6549",
            font=font_medium,
        )
        image.save(output_path)
        return output_path


def get_image_generator(provider: str) -> ImageGenerator:
    if provider == "placeholder":
        return PlaceholderImageGenerator()
    if provider == "replicate":
        return ReplicateImageGenerator()
    raise ValueError(f"Provider '{provider}' ainda nao foi configurado.")


class ReplicateImageGenerator:
    model = "black-forest-labs/flux-kontext-pro"
    landmark_model = "black-forest-labs/flux-schnell"

    def generate_cover(
        self,
        family_photo: Path,
        output_path: Path,
        title: str,
        destination_names: list[str],
    ) -> Path:
        import replicate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = cover_prompt(title=title, destination_names=destination_names)
        with family_photo.open("rb") as image_file:
            output = _run_replicate_with_retry(
                replicate,
                self.model,
                input={
                    "prompt": prompt,
                    "input_image": image_file,
                    "aspect_ratio": "3:4",
                    "output_format": "png",
                },
                wait=60,
            )
        _write_replicate_output(output, output_path)
        return output_path

    def generate_landmark_image(
        self,
        landmark_name: str,
        city: str,
        country: str,
        output_path: Path,
    ) -> Path:
        import replicate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = landmark_prompt(
            landmark_name=landmark_name,
            city=city,
            country=country,
        )
        output = _run_replicate_with_retry(
            replicate,
            self.landmark_model,
            input={
                "prompt": prompt,
                "aspect_ratio": "4:3",
                "output_format": "png",
                "num_outputs": 1,
            },
        )
        _write_replicate_output(output, output_path)
        return output_path


def cover_prompt(title: str, destination_names: list[str]) -> str:
    landmarks = ", ".join(destination_names)
    return (
        "Transform the reference photo into a polished children's book watercolor "
        "illustration for a personalized family travel guide cover. Preserve the "
        "main couple's recognizable composition, friendly smiles, approximate hair "
        "colors, glasses, and pose, but render them as soft illustrated characters, "
        "not a photorealistic copy. Use warm natural light, soft pastel colors, "
        "and a subtle background inspired by these confirmed tourist landmarks: "
        f"{landmarks}. "
        "Vertical cover composition, generous clean space for title text added later. "
        f"Do not include any readable text, logos, watermark, or the title '{title}' "
        "inside the image."
    )


def landmark_prompt(landmark_name: str, city: str, country: str) -> str:
    return (
        f"Representative exterior view of {landmark_name} in {city}, {country}. "
        "Polished children's book watercolor illustration matching a premium family "
        "travel guide cover, soft pastel colors, warm natural light, gentle paper "
        "texture, soft illustrated edges, clean vertical-friendly editorial composition, "
        "charming but accurate landmark exterior, calm open sky, subtle travel-book mood, "
        "no readable text, no labels, no watermark, no logo, no signature."
    )


def _write_replicate_output(output: object, output_path: Path) -> None:
    candidate = output[0] if isinstance(output, list) else output
    if hasattr(candidate, "read"):
        output_path.write_bytes(candidate.read())
        return
    if isinstance(candidate, str):
        import httpx

        response = httpx.get(candidate, timeout=120)
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return
    if isinstance(candidate, bytes):
        output_path.write_bytes(candidate)
        return
    raise TypeError(f"Unsupported Replicate output type: {type(candidate)!r}")


def _run_replicate_with_retry(replicate_module, model: str, **kwargs: object) -> object:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            return replicate_module.run(model, **kwargs)
        except Exception as error:
            last_error = error
            if "429" not in str(error) and "throttled" not in str(error).lower():
                raise
            sleep(10 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()
