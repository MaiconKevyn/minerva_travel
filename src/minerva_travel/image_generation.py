from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any, Literal, Protocol, cast
from unicodedata import normalize

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError


@dataclass(frozen=True)
class CoverValidationResult:
    status: Literal["passed", "failed", "unavailable", "inconclusive"]
    visible_people_count: int | None = None
    message: str = ""


@dataclass(frozen=True)
class CoverGenerationResult:
    image_path: Path
    fallback_used: bool
    validation: CoverValidationResult | None = None
    attempts: int = 1


class CoverImageValidator(Protocol):
    def validate(
        self,
        image_path: Path,
        expected_visible_family_member_count: int,
    ) -> CoverValidationResult:
        """Validate whether generated cover output preserves the expected person count."""


class ImageGenerator(Protocol):
    def generate_cover(
        self,
        family_photo: Path,
        output_path: Path,
        title: str,
        destination_names: list[str],
        *,
        expected_visible_family_member_count: int | None = None,
    ) -> Path:
        """Generate a cover image and return its local path."""

    def generate_trip_summary(
        self,
        output_path: Path,
        title: str,
        destination_names: list[str],
    ) -> Path:
        """Generate an illustrated route-map summary and return its local path."""

    def generate_landmark_image(
        self,
        landmark_name: str,
        city: str,
        country: str,
        output_path: Path,
    ) -> Path:
        """Generate an image for a tourist landmark and return its local path."""

    def generate_landmark_lineart(
        self,
        landmark_name: str,
        city: str,
        country: str,
        reference_image: Path,
        output_path: Path,
    ) -> Path:
        """Generate a black-and-white coloring image for a tourist landmark."""


class PlaceholderImageGenerator:
    def generate_cover(
        self,
        family_photo: Path,
        output_path: Path,
        title: str,
        destination_names: list[str],
        *,
        expected_visible_family_member_count: int | None = None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (1200, 1600), "#f7efe3")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (90, 90, 1110, 1510),
            radius=36,
            fill="#fffaf1",
            outline="#6a93b8",
            width=6,
        )
        photo = _safe_cover_photo(family_photo, size=(920, 900))
        if photo is not None:
            mask = Image.new("L", photo.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, *photo.size), radius=42, fill=255)
            image.paste(photo, (140, 145), mask)
            draw.rounded_rectangle(
                (130, 135, 1070, 1065),
                radius=54,
                outline="#fffaf1",
                width=18,
            )
        else:
            # Development fixtures may intentionally contain invalid bytes.
            # Keep the fallback warm and generic without exposing internal
            # labels or pretending to know what the family looks like.
            draw.ellipse((170, 245, 1030, 1025), fill="#d8ebf1", outline="#89abc2", width=5)
            draw.rectangle((305, 760, 895, 1040), fill="#c9b59b", outline="#7d6549", width=5)
            people_count = _bounded_family_member_count(expected_visible_family_member_count) or 4
            start_x = 600 - ((people_count - 1) * 62)
            colors = ["#6a93b8", "#d77a61", "#83a95c", "#c9a94d", "#8d7cc3", "#69b482"]
            for index in range(people_count):
                x = start_x + (index * 124)
                draw.ellipse((x - 42, 585, x + 42, 669), fill="#f2c6a0", outline="#7d6549", width=3)
                draw.rounded_rectangle(
                    (x - 52, 670, x + 52, 860),
                    radius=28,
                    fill=colors[index % len(colors)],
                    outline="#7d6549",
                    width=3,
                )

        draw.arc((210, 1110, 990, 1470), start=190, end=345, fill="#d77a61", width=8)
        draw.ellipse((248, 1322, 280, 1354), fill="#d77a61")
        draw.ellipse((900, 1230, 932, 1262), fill="#6a93b8")
        draw.polygon([(600, 1190), (640, 1270), (600, 1250), (560, 1270)], fill="#c9a94d")
        image.save(output_path)
        return output_path

    def generate_trip_summary(
        self,
        output_path: Path,
        title: str,
        destination_names: list[str],
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (900, 1600), "#fff3df")
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle(
            (40, 40, 860, 1560),
            radius=70,
            fill="#fff8ea",
            outline="#2d7588",
            width=8,
        )
        draw.rectangle((58, 58, 842, 470), fill="#cfe9f3")
        draw.polygon(
            [
                (48, 820),
                (210, 720),
                (390, 790),
                (535, 710),
                (700, 790),
                (852, 690),
                (852, 1560),
                (48, 1560),
            ],
            fill="#cbe3b7",
        )
        draw.line(
            [(55, 1160), (260, 1050), (470, 1165), (660, 1040), (850, 1115)],
            fill="#82c4d3",
            width=120,
        )
        draw.line(
            [(55, 1160), (260, 1050), (470, 1165), (660, 1040), (850, 1115)],
            fill="#4d9db3",
            width=24,
        )

        for x, y, scale in [
            (250, 610, 0.86),
            (585, 560, 0.78),
            (390, 920, 0.68),
            (680, 895, 0.74),
        ]:
            _draw_placeholder_landmark(draw, x, y, scale)
        for x, y in [
            (125, 770),
            (745, 760),
            (190, 1015),
            (585, 1040),
            (785, 1260),
            (250, 1370),
            (510, 1360),
        ]:
            _draw_tree(draw, x, y)

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

    def generate_landmark_lineart(
        self,
        landmark_name: str,
        city: str,
        country: str,
        reference_image: Path,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (1200, 850), "white")
        draw = ImageDraw.Draw(image)
        font_large = _font(52)
        font_medium = _font(30)

        draw.rounded_rectangle((90, 90, 1110, 760), radius=30, outline="black", width=6)
        draw.ellipse((190, 145, 1010, 700), outline="black", width=4)
        draw.line((260, 650, 600, 220, 940, 650), fill="black", width=8)
        draw.rectangle((500, 650, 700, 735), outline="black", width=8)
        draw.text((600, 405), landmark_name, anchor="mm", fill="black", font=font_large)
        draw.text((600, 480), f"{city}, {country}", anchor="mm", fill="black", font=font_medium)
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
        *,
        expected_visible_family_member_count: int | None = None,
    ) -> Path:
        import replicate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = cover_prompt(
            title=title,
            destination_names=destination_names,
            expected_visible_family_member_count=expected_visible_family_member_count,
        )
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

    def generate_trip_summary(
        self,
        output_path: Path,
        title: str,
        destination_names: list[str],
    ) -> Path:
        import replicate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output = _run_replicate_with_retry(
            replicate,
            self.landmark_model,
            input={
                "prompt": trip_summary_prompt(
                    title=title,
                    destination_names=destination_names,
                ),
                "aspect_ratio": "9:16",
                "output_format": "png",
                "num_outputs": 1,
            },
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

    def generate_landmark_lineart(
        self,
        landmark_name: str,
        city: str,
        country: str,
        reference_image: Path,
        output_path: Path,
    ) -> Path:
        import replicate

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = landmark_lineart_prompt(
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


def get_cover_image_validator() -> CoverImageValidator | None:
    return None


def generate_cover_with_guardrails(
    *,
    generator: ImageGenerator,
    family_photo: Path,
    output_path: Path,
    title: str,
    destination_names: list[str],
    expected_visible_family_member_count: int | None = None,
    validator: CoverImageValidator | None = None,
) -> CoverGenerationResult:
    expected_count = _bounded_family_member_count(expected_visible_family_member_count)
    if expected_count is None:
        _generate_cover(
            generator,
            family_photo,
            output_path,
            title,
            destination_names,
            None,
        )
        return CoverGenerationResult(image_path=output_path, fallback_used=False)

    if validator is None:
        validation = CoverValidationResult(
            status="unavailable",
            message="A validação automática da ilustração não está disponível.",
        )
        write_family_cover_fallback(
            family_photo=family_photo,
            output_path=output_path,
            title=title,
            destination_names=destination_names,
            expected_visible_family_member_count=expected_count,
        )
        return CoverGenerationResult(
            image_path=output_path,
            fallback_used=True,
            validation=validation,
            attempts=0,
        )

    attempts = 0
    latest_validation: CoverValidationResult | None = None
    for _ in range(2):
        attempts += 1
        _generate_cover(
            generator,
            family_photo,
            output_path,
            title,
            destination_names,
            expected_count,
        )
        latest_validation = validator.validate(output_path, expected_count)
        if latest_validation.status == "passed":
            return CoverGenerationResult(
                image_path=output_path,
                fallback_used=False,
                validation=latest_validation,
                attempts=attempts,
            )
        if latest_validation.status != "failed":
            break

    write_family_cover_fallback(
        family_photo=family_photo,
        output_path=output_path,
        title=title,
        destination_names=destination_names,
        expected_visible_family_member_count=expected_count,
    )
    return CoverGenerationResult(
        image_path=output_path,
        fallback_used=True,
        validation=latest_validation,
        attempts=attempts,
    )


def _generate_cover(
    generator: ImageGenerator,
    family_photo: Path,
    output_path: Path,
    title: str,
    destination_names: list[str],
    expected_visible_family_member_count: int | None,
) -> Path:
    if expected_visible_family_member_count is None:
        return generator.generate_cover(
            family_photo=family_photo,
            output_path=output_path,
            title=title,
            destination_names=destination_names,
        )
    return generator.generate_cover(
        family_photo=family_photo,
        output_path=output_path,
        title=title,
        destination_names=destination_names,
        expected_visible_family_member_count=expected_visible_family_member_count,
    )


def _safe_cover_photo(photo_path: Path, *, size: tuple[int, int]) -> Image.Image | None:
    """Prepare the uploaded photo for the local, privacy-preserving cover fallback."""

    try:
        with Image.open(photo_path) as source:
            normalized = ImageOps.exif_transpose(source).convert("RGB")
            return ImageOps.fit(normalized, size, method=Image.Resampling.LANCZOS)
    except (OSError, UnidentifiedImageError):
        return None


def write_family_cover_fallback(
    *,
    family_photo: Path,
    output_path: Path,
    title: str,
    destination_names: list[str],
    expected_visible_family_member_count: int | None = None,
) -> Path:
    # Quando a ilustracao nao pode ser validada, a foto sanitizada preserva a
    # composicao real da familia e evita pagar por uma geracao que sera
    # descartada. O titulo fica no painel do template, fora da imagem.
    del title, destination_names
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1200, 1600), "#fff8ea")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((58, 58, 1142, 1542), radius=72, fill="#fdfbf7")
    draw.rounded_rectangle((110, 145, 1090, 1240), radius=44, fill="#d8ebf1")
    try:
        with Image.open(family_photo) as source:
            photo = ImageOps.exif_transpose(source).convert("RGB")
        framed = ImageOps.fit(
            photo,
            (980, 1095),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.42),
        )
        image.paste(framed, (110, 145))
    except (OSError, ValueError):
        draw.ellipse((250, 240, 950, 940), fill="#eaf4f8", outline="#9dc3d4", width=4)
        _draw_family_silhouette_fallback(
            draw,
            expected_visible_family_member_count,
        )

    image.save(output_path)
    return output_path


def _draw_family_silhouette_fallback(
    draw: ImageDraw.ImageDraw,
    expected_visible_family_member_count: int | None,
) -> None:
    people_count = _bounded_family_member_count(expected_visible_family_member_count) or 4
    start_x = 600 - ((people_count - 1) * 58)
    colors = ["#6a93b8", "#d77a61", "#83a95c", "#c9a94d", "#8d7cc3", "#69b482"]
    for index in range(people_count):
        x = start_x + (index * 116)
        draw.ellipse((x - 38, 470, x + 38, 546), fill="#f2c6a0", outline="#7d6549", width=3)
        draw.rounded_rectangle(
            (x - 48, 548, x + 48, 740),
            radius=28,
            fill=colors[index % len(colors)],
            outline="#7d6549",
            width=3,
        )


def _bounded_family_member_count(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    if count < 1:
        return None
    return min(count, 20)


def cover_prompt(
    title: str,
    destination_names: list[str],
    expected_visible_family_member_count: int | None = None,
) -> str:
    landmarks = ", ".join(destination_names)
    expected_count = _bounded_family_member_count(expected_visible_family_member_count)
    family_count_guidance = ""
    if expected_count is not None:
        family_count_guidance = (
            f"The reference photo contains exactly {expected_count} visible family "
            f"members. The illustration must include exactly {expected_count} visible "
            "family members with balanced placement and similar relative sizes. "
            "Do not omit, crop out, replace, or merge any family member. "
            "Do not turn a group photo into a portrait of only one adult or child. "
        )
    return (
        "Transform the reference photo into a polished children's book watercolor "
        "illustration for a personalized family travel guide cover. Preserve the "
        "family group's recognizable composition, friendly smiles, approximate hair "
        "colors, glasses, ages, and poses, but render them as soft illustrated "
        f"characters, not a photorealistic copy. {family_count_guidance}"
        "Use warm natural light, soft pastel colors, "
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


def trip_summary_prompt(title: str, destination_names: list[str]) -> str:
    landmarks = ", ".join(destination_names)
    return (
        "Create a vertical text-free children's book travel illustration for the "
        "left map panel of a printed itinerary page. It should feel like the scenic "
        "illustration side of a premium family travel planner, with lush watercolor "
        "and gouache detail, playful city scenery, recognizable landmark silhouettes, "
        "parks, streets, river, small boats, carousels or family-friendly details, "
        f"and warm daylight. The trip title is '{title}' and the scenery is inspired "
        f"by these confirmed places: {landmarks}. Draw only the scenery. The app will "
        "add all title text, stop names, route numbers, start/end pins, and route "
        "graphics separately. Leave clear visual space for those overlays. Do not "
        "include readable text, labels, or numbers. Do not include landmark names "
        "as text. Do not include handwriting, map labels, street names, signs, "
        "posters, banners, tickets, route markers, logos, watermarks, signatures, "
        "prices, clocks, UI elements, or any typography inside the image."
    )


def landmark_lineart_prompt(landmark_name: str, city: str, country: str) -> str:
    feature_guidance = _landmark_lineart_feature_guidance(landmark_name)
    return (
        "Create a premium children's coloring book line art page for children "
        f"ages 4 to 8 showing {landmark_name} in {city}, {country}. Use a clean "
        "front-facing editorial composition like a printed travel coloring page. "
        "Do not trace a photo. Do not make a sparse icon. Draw the landmark "
        "large and recognizable, with its main silhouette, recognizable facade, "
        "and signature feature centered on the page. "
        f"{feature_guidance}"
        "Architectural "
        "detail is allowed only when simplified: simplified rows of windows, "
        "large arches, broad doors, clean rooflines, and a few evenly spaced "
        "decorative shapes. "
        "Do not add pyramids, domes, glass roofs, flags, bridges, or modern "
        "structures unless they are actually part of the named landmark. "
        "Add a few small simple people only as friendly scale "
        "figures, drawn with very simple outlines. Use clean medium-weight black "
        "outlines, large open white areas, and clear closed shapes for crayons. "
        "Avoid realism and visual noise. Do not include tiny repeated patterns, "
        "photo texture, brick texture, shadows, reflections, hatching, stippling, "
        "speckles, messy sketch lines, grayscale, filled black areas, gradients, "
        "readable text, labels, signs, logos, watermarks, or signatures. No color."
    )


def _landmark_lineart_feature_guidance(landmark_name: str) -> str:
    normalized_name = _normalize_ascii(landmark_name)
    if any(term in normalized_name for term in ("castelo", "castle", "fortress", "fort")):
        return (
            "For castles and fortresses, draw a hilltop medieval castle with "
            "medieval fortress walls, "
            "crenellated battlements, square stone towers, an arched entrance gate, "
            "flat crenellated tops, and a simple hill or path shape. This is a medieval fortress, "
            "not a palace, cathedral, basilica, church, monastery, or museum. "
            "Do not draw domes, curved roofs, glass pyramids, palace roofs, "
            "or church facades. Do not draw cone roofs, pointed roofs, fairy-tale towers, a "
            "fantasy castle, or museum-style buildings. "
        )
    return (
        "If the landmark has a famous foreground element such as a pyramid, tower, "
        "dome, arch, bridge, or gate, make it prominent. For Louvre-style glass "
        "pyramids, use large pyramid glass panels that are easy to color, not a "
        "dense grid. "
    )


def _normalize_ascii(value: str) -> str:
    return normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()


def simplify_child_coloring_lineart(image_path: Path, output_path: Path | None = None) -> Path:
    """Normalize generated lineart into a simpler page children can actually color."""
    target_path = output_path or image_path
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("L")

    image = _to_binary_lineart(image)
    image = _normalize_lineart_scale(image)
    image = _remove_fine_lineart_texture(image)
    image = _remove_small_lineart_components(image)
    image = image.point(lambda pixel: 0 if pixel < 128 else 255).convert("RGB")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(target_path, "PNG")
    return target_path


def _to_binary_lineart(image: Image.Image) -> Image.Image:
    image = ImageOps.autocontrast(image, cutoff=1)
    return image.point(lambda pixel: 0 if pixel < 190 else 255).convert("L")


def _normalize_lineart_scale(image: Image.Image) -> Image.Image:
    black_mask = image.point(lambda pixel: 255 if pixel < 128 else 0).convert("L")
    bbox = black_mask.getbbox()
    if not bbox:
        return image

    padding = max(12, int(min(image.size) * 0.04))
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    cropped = image.crop((left, top, right, bottom))
    cropped.thumbnail(
        (int(image.width * 0.9), int(image.height * 0.86)),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("L", image.size, 255)
    x = (canvas.width - cropped.width) // 2
    y = (canvas.height - cropped.height) // 2
    canvas.paste(cropped, (x, y))
    return canvas.point(lambda pixel: 0 if pixel < 190 else 255).convert("L")


def _remove_fine_lineart_texture(image: Image.Image) -> Image.Image:
    return image.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))


def _remove_small_lineart_components(
    image: Image.Image,
    min_pixels: int = 40,
) -> Image.Image:
    grayscale = image.convert("L")
    width, height = grayscale.size
    total_pixels = width * height
    pixels = cast(Iterable[int], grayscale.get_flattened_data())
    black_pixels = bytearray(1 if pixel < 128 else 0 for pixel in pixels)
    visited = bytearray(total_pixels)
    keep = bytearray(total_pixels)

    for start in range(total_pixels):
        if not black_pixels[start] or visited[start]:
            continue

        stack = [start]
        visited[start] = 1
        component: list[int] = []
        while stack:
            index = stack.pop()
            component.append(index)
            x = index % width
            y = index // width
            for next_x, next_y in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if next_x < 0 or next_x >= width or next_y < 0 or next_y >= height:
                    continue
                next_index = next_y * width + next_x
                if black_pixels[next_index] and not visited[next_index]:
                    visited[next_index] = 1
                    stack.append(next_index)

        if len(component) >= min_pixels:
            for index in component:
                keep[index] = 1

    cleaned = Image.new("L", grayscale.size, 255)
    cleaned.putdata([0 if pixel else 255 for pixel in keep])
    return cleaned


def _write_replicate_output(output: object, output_path: Path) -> None:
    candidate = output[0] if isinstance(output, list) else output
    if hasattr(candidate, "read"):
        output_path.write_bytes(_read_replicate_file_output(candidate))
        return
    if isinstance(candidate, str):
        output_path.write_bytes(_download_replicate_url(candidate))
        return
    if isinstance(candidate, bytes):
        output_path.write_bytes(candidate)
        return
    raise TypeError(f"Unsupported Replicate output type: {type(candidate)!r}")


def _read_replicate_file_output(candidate: Any) -> bytes:
    def operation() -> bytes:
        return candidate.read()

    return _run_download_with_retry(operation)


def _download_replicate_url(url: str) -> bytes:
    import httpx

    def operation() -> bytes:
        response = httpx.get(url, timeout=120)
        response.raise_for_status()
        return response.content

    return _run_download_with_retry(operation)


def _run_download_with_retry(operation) -> bytes:
    import httpx

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            return operation()
        except (httpx.HTTPError, OSError) as error:
            last_error = error
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500:
                raise
            sleep(2 * (attempt + 1))
    assert last_error is not None
    raise last_error


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


def _draw_placeholder_landmark(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    scale: float,
) -> None:
    width = int(90 * scale)
    height = int(210 * scale)
    draw.rectangle(
        (x - width, y + height // 3, x + width, y + height),
        fill="#efd9b5",
        outline="#7d6549",
        width=4,
    )
    draw.polygon(
        (x, y, x - width, y + height // 3, x + width, y + height // 3),
        fill="#d77a61",
        outline="#7d6549",
    )
    for offset in (-45, 0, 45):
        window_x = x + int(offset * scale)
        draw.rectangle(
            (window_x - 16, y + height // 2, window_x + 16, y + height - 26),
            fill="#92bed1",
            outline="#7d6549",
            width=2,
        )


def _draw_tree(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rectangle((x - 10, y + 28, x + 10, y + 85), fill="#8a5f3d")
    draw.ellipse((x - 50, y - 20, x + 50, y + 65), fill="#6fa15f", outline="#497f47", width=3)
    draw.ellipse((x - 26, y - 50, x + 36, y + 35), fill="#88b08b", outline="#497f47", width=3)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()
