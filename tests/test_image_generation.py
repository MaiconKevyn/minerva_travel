import sys
from types import SimpleNamespace

from minerva_travel.image_generation import (
    PlaceholderImageGenerator,
    ReplicateImageGenerator,
    cover_prompt,
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


def test_replicate_image_generator_writes_file_output(tmp_path, monkeypatch):
    source = tmp_path / "family.png"
    output = tmp_path / "cover.png"
    source.write_bytes(b"source")

    class FakeFileOutput:
        def read(self):
            return b"generated-image"

    def fake_run(model, input, wait):
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
