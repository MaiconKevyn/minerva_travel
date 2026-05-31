import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minerva_travel.config import load_project_env
from minerva_travel.image_generation import ReplicateImageGenerator


def main() -> None:
    load_project_env()
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/20250601_104614.jpg")
    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path("runtime/generated/replicate-cover-test.png")
    )
    generator = ReplicateImageGenerator()
    result = generator.generate_cover(
        family_photo=input_path,
        output_path=output_path,
        title="Pequenos Exploradores pela Europa",
        destination_names=["Paris", "Londres", "Cambridge", "Lisboa"],
    )
    print(result)


if __name__ == "__main__":
    main()
