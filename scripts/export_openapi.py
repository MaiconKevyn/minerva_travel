"""Export or verify the deterministic OpenAPI contract consumed by the frontend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from minerva_travel.app import app

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "frontend_atual/apps/web/src/contracts/minerva-openapi.json"


def rendered_openapi() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = args.output.resolve()
    rendered = rendered_openapi()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            parser.error(
                "OpenAPI snapshot is stale: run "
                f"`python {Path(__file__).name}` and commit {output}."
            )
        print(f"OpenAPI snapshot is current: {output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Wrote OpenAPI snapshot: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
