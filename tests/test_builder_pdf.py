from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from minerva_travel.pdf import ApprovedPagePdfError, write_approved_page_images_pdf


def _page(path: Path, color: str) -> Path:
    Image.new("RGB", (1024, 1536), color).save(path, format="PNG")
    return path


def test_approved_images_fill_pdf_pages_in_the_supplied_order(tmp_path):
    colors = ("#d34f4f", "#4f86b7", "#69b482")
    pages = [_page(tmp_path / f"page-{index}.png", color) for index, color in enumerate(colors)]
    output = tmp_path / "output" / "approved-guide.pdf"

    assert write_approved_page_images_pdf(pages, output, title="Família Aurora") == output

    reader = PdfReader(output)
    assert len(reader.pages) == 3
    expected_rgb = ((211, 79, 79), (79, 134, 183), (105, 180, 130))
    for page, color in zip(reader.pages, expected_rgb, strict=True):
        assert float(page.mediabox.width) == pytest.approx(432)
        assert float(page.mediabox.height) == pytest.approx(648)
        assert page.extract_text() == ""
        rendered = page.images[0].image.convert("RGB")
        assert rendered.getpixel((rendered.width // 2, rendered.height // 2)) == color
    assert output.stat().st_mode & 0o777 == 0o600


def test_approved_pdf_rejects_invalid_pages_without_leaving_partial_output(tmp_path):
    invalid = tmp_path / "wrong-size.png"
    Image.new("RGB", (512, 512), "#ffffff").save(invalid, format="PNG")
    output = tmp_path / "approved-guide.pdf"

    with pytest.raises(ApprovedPagePdfError, match="dimensões"):
        write_approved_page_images_pdf([invalid], output)

    assert not output.exists()
    assert not output.with_suffix(".pdf.tmp").exists()
