import sys
from types import SimpleNamespace

import httpx
from PIL import Image, ImageDraw

from minerva_travel.image_generation import (
    CoverValidationResult,
    PlaceholderImageGenerator,
    ReplicateImageGenerator,
    _write_replicate_output,
    cover_prompt,
    generate_cover_with_guardrails,
    landmark_lineart_prompt,
    simplify_child_coloring_lineart,
    trip_summary_prompt,
)


def test_placeholder_image_generator_creates_cover(tmp_path):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    source.write_bytes(b"not-a-real-image")

    generator = PlaceholderImageGenerator()
    result = generator.generate_cover(
        family_photo=source,
        output_path=output,
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris", "Londres"],
    )

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 1000


def test_cover_prompt_avoids_text_inside_image():
    prompt = cover_prompt(
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris", "Londres"],
    )

    assert "Do not include any readable text" in prompt
    assert "Paris, Londres" in prompt


def test_cover_prompt_preserves_expected_family_member_count():
    prompt_for_two = cover_prompt(
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris"],
        expected_visible_family_member_count=2,
    )
    prompt_for_three = cover_prompt(
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris"],
        expected_visible_family_member_count=3,
    )
    prompt_for_four = cover_prompt(
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris"],
        expected_visible_family_member_count=4,
    )

    assert "exactly 2 visible family members" in prompt_for_two
    assert "exactly 3 visible family members" in prompt_for_three
    assert "exactly 4 visible family members" in prompt_for_four
    assert "Do not omit, crop out, replace, or merge any family member" in prompt_for_four


def test_cover_guardrail_falls_back_when_validation_fails(tmp_path):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    Image.new("RGB", (640, 480), "#90c4df").save(source)

    class FakeGenerator:
        calls = 0

        def generate_cover(
            self,
            family_photo,
            output_path,
            title,
            destination_names,
            *,
            expected_visible_family_member_count=None,
        ):
            self.calls += 1
            output_path.write_bytes(f"bad-cover-{self.calls}".encode())
            return output_path

    class FailingValidator:
        def validate(self, image_path, expected_visible_family_member_count):
            return CoverValidationResult(
                status="failed",
                visible_people_count=1,
                message="Only one person detected",
            )

    generator = FakeGenerator()

    result = generate_cover_with_guardrails(
        generator=generator,
        family_photo=source,
        output_path=output,
        title="Família Silva",
        destination_names=["Paris"],
        expected_visible_family_member_count=4,
        validator=FailingValidator(),
    )

    assert generator.calls == 2
    assert result.fallback_used is True
    assert result.validation.status == "failed"
    assert result.validation.visible_people_count == 1
    assert output.exists()
    with Image.open(output) as fallback:
        assert fallback.size == (1200, 1600)


def test_cover_guardrail_keeps_generated_cover_when_validation_passes(tmp_path):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    source.write_bytes(b"source")

    class FakeGenerator:
        def generate_cover(
            self,
            family_photo,
            output_path,
            title,
            destination_names,
            *,
            expected_visible_family_member_count=None,
        ):
            assert expected_visible_family_member_count == 4
            output_path.write_bytes(b"generated-cover")
            return output_path

    class PassingValidator:
        def validate(self, image_path, expected_visible_family_member_count):
            return CoverValidationResult(
                status="passed",
                visible_people_count=4,
            )

    result = generate_cover_with_guardrails(
        generator=FakeGenerator(),
        family_photo=source,
        output_path=output,
        title="Família Silva",
        destination_names=["Paris"],
        expected_visible_family_member_count=4,
        validator=PassingValidator(),
    )

    assert result.fallback_used is False
    assert result.validation.status == "passed"
    assert output.read_bytes() == b"generated-cover"


def test_cover_guardrail_skips_paid_generation_when_validator_is_unavailable(tmp_path):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    Image.new("RGB", (640, 480), "#90c4df").save(source)

    class GeneratorThatMustNotRun:
        def generate_cover(self, *args, **kwargs):
            raise AssertionError("generation should be skipped without a validator")

    result = generate_cover_with_guardrails(
        generator=GeneratorThatMustNotRun(),
        family_photo=source,
        output_path=output,
        title="Família Silva",
        destination_names=["Paris"],
        expected_visible_family_member_count=4,
        validator=None,
    )

    assert result.fallback_used is True
    assert result.validation.status == "unavailable"
    assert result.attempts == 0
    with Image.open(output) as cover:
        assert cover.convert("RGB").getpixel((600, 500)) == (144, 196, 223)


def test_cover_guardrail_keeps_backward_compatible_generation_without_expected_count(tmp_path):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    source.write_bytes(b"source")

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"legacy-cover")
            return output_path

    result = generate_cover_with_guardrails(
        generator=FakeGenerator(),
        family_photo=source,
        output_path=output,
        title="Família Silva",
        destination_names=["Paris"],
    )

    assert result.fallback_used is False
    assert result.validation is None
    assert output.read_bytes() == b"legacy-cover"


def test_placeholder_image_generator_creates_trip_summary(tmp_path):
    output = tmp_path / "summary.png"

    generator = PlaceholderImageGenerator()
    result = generator.generate_trip_summary(
        output_path=output,
        title="Pequenos Exploradores pela Europa",
        destination_names=["Museu do Louvre", "Gallery of Evolution", "Torre Eiffel"],
    )

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 1000


def test_trip_summary_prompt_asks_for_illustrated_route_without_text():
    prompt = trip_summary_prompt(
        title="Pequenos Exploradores pela Europa",
        destination_names=["Museu do Louvre", "Gallery of Evolution"],
    )

    assert "vertical text-free children's book travel illustration" in prompt
    assert "Museu do Louvre, Gallery of Evolution" in prompt
    assert "Do not include readable text" in prompt
    assert "Do not include landmark names" in prompt


def test_replicate_image_generator_writes_file_output(tmp_path, monkeypatch):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    source.write_bytes(b"source")

    class FakeFileOutput:
        def read(self):
            return b"generated-image"

    def fake_run(model, input, wait=None):
        assert model == "black-forest-labs/flux-kontext-pro"
        assert "input_image" in input
        assert wait == 60
        return [FakeFileOutput()]

    monkeypatch.setitem(sys.modules, "replicate", SimpleNamespace(run=fake_run))

    result = ReplicateImageGenerator().generate_cover(
        family_photo=source,
        output_path=output,
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris"],
    )

    assert result == output
    assert output.read_bytes() == b"generated-image"


def test_replicate_output_download_retries_transient_read_errors(tmp_path, monkeypatch):
    output = tmp_path / "image.png"

    class FlakyFileOutput:
        attempts = 0

        def read(self):
            self.attempts += 1
            if self.attempts == 1:
                raise httpx.ReadError("Connection reset by peer")
            return b"generated-after-retry"

    monkeypatch.setattr("minerva_travel.image_generation.sleep", lambda _: None)

    _write_replicate_output([FlakyFileOutput()], output)

    assert output.read_bytes() == b"generated-after-retry"


def test_landmark_lineart_prompt_requests_premium_clean_coloring_page():
    prompt = landmark_lineart_prompt(
        landmark_name="Museu do Louvre",
        city="Paris",
        country="Franca",
    )

    assert "premium children's coloring book line art page" in prompt
    assert "children ages 4 to 8" in prompt
    assert "front-facing editorial composition" in prompt
    assert "recognizable facade" in prompt
    assert "simplified rows of windows" in prompt
    assert "large pyramid glass panels" in prompt
    assert "small simple people" in prompt
    assert "large open white areas" in prompt
    assert "Do not trace a photo" in prompt
    assert "Do not make a sparse icon" in prompt
    assert "Do not add pyramids, domes, glass roofs" in prompt
    assert "tiny repeated patterns" in prompt
    assert "Museu do Louvre" in prompt
    assert "No color" in prompt


def test_landmark_lineart_prompt_adds_castle_specific_guidance():
    prompt = landmark_lineart_prompt(
        landmark_name="Castelo de S. Jorge",
        city="Lisboa",
        country="Portugal",
    )

    assert "medieval fortress walls" in prompt
    assert "crenellated battlements" in prompt
    assert "square stone towers" in prompt
    assert "arched entrance gate" in prompt
    assert "hilltop medieval castle" in prompt
    assert "flat crenellated tops" in prompt
    assert "not a palace, cathedral, basilica, church, monastery, or museum" in prompt
    assert "Do not draw domes" in prompt
    assert "Do not draw cone roofs" in prompt
    assert "fantasy castle" in prompt


def test_simplify_child_coloring_lineart_removes_tiny_texture(tmp_path):
    source = tmp_path / "busy-lineart.png"
    image = Image.new("L", (180, 120), 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 170, 110), outline=0, width=6)
    for x in range(24, 156, 4):
        draw.line((x, 34, x, 86), fill=0, width=1)
    for y in range(36, 84, 4):
        draw.line((26, y, 154, y), fill=0, width=1)
    image.save(source)

    before = _count_black_pixels(source)

    simplify_child_coloring_lineart(source)

    after = _count_black_pixels(source)
    assert after > 1_500
    assert after < before * 0.55


def test_replicate_lineart_generates_simple_drawing_without_tracing_reference(
    tmp_path,
    monkeypatch,
):
    reference = tmp_path / "landmark.png"
    output = tmp_path / "lineart.png"
    reference.write_bytes(b"reference-image")

    class FakeFileOutput:
        def read(self):
            image = Image.new("RGB", (40, 30), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((4, 4, 36, 26), outline="black", width=3)
            draw.line((10, 15, 30, 15), fill=(172, 172, 172), width=1)
            png = tmp_path / "generated-lineart.png"
            image.save(png)
            return png.read_bytes()

    def fake_run(model, input, wait=None):
        assert model == "black-forest-labs/flux-schnell"
        assert "input_image" not in input
        assert input["aspect_ratio"] == "4:3"
        assert "Do not trace a photo" in input["prompt"]
        assert wait is None
        return [FakeFileOutput()]

    monkeypatch.setitem(sys.modules, "replicate", SimpleNamespace(run=fake_run))

    result = ReplicateImageGenerator().generate_landmark_lineart(
        landmark_name="Cristo Redentor",
        city="Rio de Janeiro",
        country="Brasil",
        reference_image=reference,
        output_path=output,
    )

    assert result == output
    assert output.exists()
    with Image.open(output) as image:
        assert image.convert("RGB").getpixel((20, 15)) == (172, 172, 172)


def _count_black_pixels(path):
    with Image.open(path) as image:
        grayscale = image.convert("L")
        return sum(1 for pixel in grayscale.getdata() if pixel < 128)


def test_family_cover_fallback_preserves_sanitized_family_photo(tmp_path):
    from minerva_travel.image_generation import write_family_cover_fallback

    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    Image.new("RGB", (640, 480), "#90c4df").save(source)

    result = write_family_cover_fallback(
        family_photo=source,
        output_path=output,
        title="Familia Moraes",
        destination_names=["Torre Eiffel"],
        expected_visible_family_member_count=3,
    )

    assert result == output
    with Image.open(output) as cover:
        assert cover.size == (1200, 1600)
        assert cover.convert("RGB").getpixel((600, 500)) == (144, 196, 223)
