from collections import defaultdict
from pathlib import Path

from minerva_travel.models import Catalog, GuideContext, GuideDestination, GuideRequest, Landmark
from minerva_travel.wikimedia_assets import ImageCredit, WikimediaAsset


def build_guide_context(
    request: GuideRequest,
    catalog: Catalog,
    cover_image: Path,
    wikimedia_assets: dict[str, WikimediaAsset] | None = None,
    landmark_images: dict[str, Path] | None = None,
    landmark_lineart_images: dict[str, Path] | None = None,
) -> GuideContext:
    wikimedia_assets = wikimedia_assets or {}
    landmark_images = landmark_images or {}
    landmark_lineart_images = landmark_lineart_images or {}
    selected_by_destination: dict[str, set[str]] = defaultdict(set)
    for selected in request.selected_landmarks:
        destination_id, landmark_id = selected.split(":", maxsplit=1)
        selected_by_destination[destination_id].add(landmark_id)

    guide_destinations: list[GuideDestination] = []
    for destination in catalog.destinations:
        selected_ids = selected_by_destination.get(destination.id, set())
        if not selected_ids:
            continue
        landmarks: list[Landmark] = []
        for landmark in destination.landmarks:
            if landmark.id not in selected_ids:
                continue
            selection_id = f"{destination.id}:{landmark.id}"
            asset = wikimedia_assets.get(selection_id)
            generated_image = landmark_images.get(selection_id)
            generated_lineart = landmark_lineart_images.get(selection_id)
            if generated_image:
                landmarks.append(
                    landmark.model_copy(
                        update={
                            "image": generated_image,
                            "lineart_image": generated_lineart or landmark.lineart_image,
                        }
                    )
                )
            elif asset:
                landmarks.append(landmark.model_copy(update={"image": asset.local_path}))
            else:
                landmarks.append(landmark)
        if landmarks:
            guide_destinations.append(
                GuideDestination(destination=destination, landmarks=landmarks)
            )

    return GuideContext(
        request=request,
        cover_image=cover_image,
        destinations=guide_destinations,
        image_credits=_collect_credits(request, catalog, wikimedia_assets),
    )


def _collect_credits(
    request: GuideRequest,
    catalog: Catalog,
    wikimedia_assets: dict[str, WikimediaAsset],
) -> list[ImageCredit]:
    selected = set(request.selected_landmarks)
    credits: list[ImageCredit] = []
    for destination in catalog.destinations:
        for landmark in destination.landmarks:
            selection_id = f"{destination.id}:{landmark.id}"
            asset = wikimedia_assets.get(selection_id)
            if selection_id in selected and asset:
                credits.append(
                    ImageCredit(
                        landmark_name=landmark.name,
                        source_url=asset.source_url,
                        author=asset.author,
                        license_short_name=asset.license_short_name,
                        license_url=asset.license_url,
                        credit=asset.credit,
                    )
                )
    return credits
