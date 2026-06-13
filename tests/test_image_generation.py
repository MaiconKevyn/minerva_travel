import sys
from types import SimpleNamespace

import httpx
from PIL import Image, ImageDraw

from minerva_travel.image_generation import (
    PlaceholderImageGenerator,
    ReplicateImageGenerator,
    _write_replicate_output,
    cover_prompt,
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


def test_landmark_lineart_prompt_requests_simple_child_coloring_page():
    prompt = landmark_lineart_prompt(
        landmark_name="Cristo Redentor",
        city="Rio de Janeiro",
        country="Brasil",
    )

    assert "Create an ultra simple black and white kindergarten coloring page" in prompt
    assert "children ages 4 to 8" in prompt
    assert "large open white areas" in prompt
    assert "2 to 4 major interior lines" in prompt
    assert "Do not trace a photo" in prompt
    assert "Do not draw windows" in prompt
    assert "tiny repeated patterns" in prompt
    assert "Cristo Redentor" in prompt
    assert "No color" in prompt


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
            draw.rectangle((4, 4, 36, 26), outline="black", width=4)
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


def _count_black_pixels(path):
    with Image.open(path) as image:
        grayscale = image.convert("L")
        return sum(1 for pixel in grayscale.getdata() if pixel < 128)
