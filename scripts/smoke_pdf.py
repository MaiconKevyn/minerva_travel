"""Generate a deterministic guide PDF without external services."""

from argparse import ArgumentParser
from pathlib import Path

from minerva_travel.catalog import load_catalog
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.models import GuideRequest
from minerva_travel.pdf import write_pdf
from minerva_travel.wikimedia_assets import load_wikimedia_manifest


def generate_smoke_pdf(output_path: Path) -> Path:
    catalog = load_catalog()
    request = GuideRequest(
        title="Minerva Travel - CI Smoke",
        children_names=["Alice"],
        children_ages=[7],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    assets = load_wikimedia_manifest()
    eiffel_asset = assets.get("paris:eiffel-tower")
    if eiffel_asset is None or not eiffel_asset.local_path.is_file():
        raise RuntimeError("The reviewed Eiffel Tower asset is required for the PDF smoke test.")
    context = build_guide_context(
        request,
        catalog,
        eiffel_asset.local_path,
        wikimedia_assets=assets,
    )
    result = write_pdf(context, output_path)

    if result.stat().st_size <= 1_000 or result.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(f"Invalid PDF generated at {result}")
    return result


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("runtime/ci/minerva-smoke.pdf"),
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = generate_smoke_pdf(args.output)
    print(f"PDF smoke generated: {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
