import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minerva_travel.catalog import load_catalog
from minerva_travel.wikimedia_assets import WikimediaAsset
from minerva_travel.wikimedia_client import USER_AGENT, fetch_landmark_asset


def main() -> None:
    limit, targets, force = parse_args(sys.argv[1:])
    output_dir = Path("runtime/wikimedia")
    manifest_path = output_dir / "manifest.json"
    catalog = load_catalog()
    assets = load_existing_assets(manifest_path)
    missing = []

    with httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for destination in catalog.destinations:
            for landmark in destination.landmarks:
                if limit is not None and len(assets) >= limit:
                    save_manifest(manifest_path, assets)
                    print_report(assets, missing, manifest_path)
                    return

                selection_id = f"{destination.id}:{landmark.id}"
                if targets and selection_id not in targets:
                    continue
                cached_selection_ids = {asset.selection_id for asset in assets}
                if selection_id in cached_selection_ids and not force:
                    print(f"Skipping {selection_id}: already cached", flush=True)
                    continue
                print(f"Fetching {selection_id}...", flush=True)
                try:
                    asset = fetch_landmark_asset(client, destination, landmark, output_dir)
                except httpx.HTTPStatusError as error:
                    print(f"  failed: HTTP {error.response.status_code}", flush=True)
                    missing.append(selection_id)
                    continue

                if asset:
                    print(f"  saved: {asset.local_path}", flush=True)
                    assets = [
                        existing
                        for existing in assets
                        if existing.selection_id != selection_id
                    ]
                    assets.append(asset)
                    save_manifest(manifest_path, assets)
                else:
                    print("  missing: no allowed image found", flush=True)
                    missing.append(selection_id)

    print_report(assets, missing, manifest_path)


def save_manifest(manifest_path: Path, assets: list[object]) -> None:
    manifest = {"assets": [asset.model_dump(mode="json") for asset in assets]}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_existing_assets(manifest_path: Path) -> list[WikimediaAsset]:
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [WikimediaAsset.model_validate(item) for item in data.get("assets", [])]


def parse_args(args: list[str]) -> tuple[int | None, set[str], bool]:
    force = "--force" in args
    args = [arg for arg in args if arg != "--force"]
    if not args:
        return None, set(), force
    if len(args) == 1 and args[0].isdigit():
        return int(args[0]), set(), force
    return None, set(args), force


def print_report(assets: list[object], missing: list[str], manifest_path: Path) -> None:
    print(f"Saved {len(assets)} Wikimedia assets to {manifest_path}")
    if missing:
        print("Missing Wikimedia assets:")
        for selection_id in missing:
            print(f"- {selection_id}")


if __name__ == "__main__":
    main()
