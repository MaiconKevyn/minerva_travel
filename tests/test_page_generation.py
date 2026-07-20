import base64
from io import BytesIO

import httpx
import pytest
from PIL import Image

from minerva_travel.page_generation import (
    OpenAIGuidePageGenerator,
    PageGenerationConfigurationError,
    PageGenerationError,
    cover_page_prompt,
    summary_page_prompt,
)


def _png_bytes(size=(1024, 1536), color="#4f86b7") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _response(image_bytes: bytes) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    return httpx.Response(
        200,
        request=request,
        json={"data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}]},
    )


def test_cover_prompt_requires_exact_family_copy_and_visible_people():
    prompt = cover_page_prompt(
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        expected_visible_family_member_count=4,
    )

    assert '"Família Moraes"' in prompt
    assert '"Julho de 2026"' in prompt
    assert "exactly 4 visible people" in prompt
    assert "verbatim" in prompt
    assert "Do not include any other readable text" in prompt


def test_summary_prompt_lists_every_stop_as_exact_copy():
    prompt = summary_page_prompt(
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
    )

    assert '1. "Torre Eiffel"' in prompt
    assert '2. "Museu do Louvre"' in prompt
    assert '"Nosso roteiro"' in prompt
    assert "Do not invent, merge or omit stops" in prompt


def test_openai_cover_uses_official_edit_contract_and_persists_png(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes())

    photo = tmp_path / "family.png"
    photo.write_bytes(_png_bytes(size=(400, 300)))
    output = tmp_path / "cover.png"
    generator = OpenAIGuidePageGenerator(
        api_key="test-key",
        model="gpt-image-2",
        quality="low",
        transport=transport,
    )

    assert (
        generator.generate_cover_page(
            family_photo=photo,
            output_path=output,
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
            expected_visible_family_member_count=3,
        )
        == output
    )
    method, url, kwargs = calls[0]
    assert method == "POST"
    assert url.endswith("/images/edits")
    assert kwargs["data"]["model"] == "gpt-image-2"
    assert "input_fidelity" not in kwargs["data"]
    assert kwargs["data"]["size"] == "1024x1536"
    assert [field for field, _file in kwargs["files"]] == ["image[]"]
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        assert image.format == "PNG"


def test_openai_summary_uses_generation_contract(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#69b482"))

    output = tmp_path / "summary.png"
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    generator.generate_summary_page(
        output_path=output,
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
    )
    _method, url, kwargs = calls[0]
    assert url.endswith("/images/generations")
    assert kwargs["json"]["output_format"] == "png"
    assert '"Coliseu"' in kwargs["json"]["prompt"]


def test_cover_revision_uses_original_photo_selected_cover_and_user_feedback(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#8f6cb3"))

    photo = tmp_path / "family.png"
    photo.write_bytes(_png_bytes(size=(400, 300)))
    reference = tmp_path / "cover-1.png"
    reference.write_bytes(_png_bytes())
    generator = OpenAIGuidePageGenerator(
        api_key="test-key", model="gpt-image-2", transport=transport
    )

    generator.generate_cover_page(
        family_photo=photo,
        reference_page=reference,
        revision_instruction="Mude o estilo para animação 3D e use tons azuis.",
        output_path=tmp_path / "cover-2.png",
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        expected_visible_family_member_count=3,
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [field for field, _file in kwargs["files"]] == ["image[]", "image[]"]
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "family.png",
        "cover-1.png",
    ]
    prompt = kwargs["data"]["prompt"]
    assert "Input image 1 is the original family photo" in prompt
    assert '"Mude o estilo para animação 3D e use tons azuis."' in prompt
    assert "requested visual style replaces" in prompt
    assert '"Família Moraes"' in prompt
    assert "change the required family member count" in prompt


def test_summary_revision_uses_selected_page_and_visible_variation_default(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#cc825f"))

    reference = tmp_path / "summary-1.png"
    reference.write_bytes(_png_bytes())
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    generator.generate_summary_page(
        output_path=tmp_path / "summary-2.png",
        reference_page=reference,
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == ["summary-1.png"]
    assert "Create a visibly different alternative" in kwargs["data"]["prompt"]
    assert '2. "Coliseu"' in kwargs["data"]["prompt"]


def test_openai_page_generator_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(PageGenerationConfigurationError):
        OpenAIGuidePageGenerator(api_key="")


def test_openai_page_generator_rejects_wrong_dimensions(tmp_path):
    def transport(_method, _url, **_kwargs):
        return _response(_png_bytes(size=(512, 512)))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    with pytest.raises(PageGenerationError, match="dimensões"):
        generator.generate_summary_page(
            output_path=tmp_path / "bad.png",
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
        )


def test_openai_error_exposes_only_safe_diagnostic_identifiers(tmp_path):
    def transport(_method, url, **_kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            400,
            request=request,
            json={
                "error": {
                    "code": "invalid_input_fidelity_model",
                    "type": "image_generation_user_error",
                    "param": "input_fidelity",
                    "message": "private family prompt must never reach the UI",
                }
            },
        )

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    with pytest.raises(PageGenerationError) as captured:
        generator.generate_summary_page(
            output_path=tmp_path / "bad.png",
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
        )

    assert "code=invalid_input_fidelity_model" in str(captured.value)
    assert "private family prompt" not in str(captured.value)
