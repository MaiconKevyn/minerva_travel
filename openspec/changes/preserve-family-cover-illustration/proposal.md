## Why

Families may upload a group photo expecting the guide cover illustration to represent everyone, but the current generation can visually drop people from the source image. This breaks trust because the cover is one of the most personal parts of the product.

## What Changes

- Add a family-cover generation contract that preserves the visible family group from the uploaded photo.
- Add prompt and metadata handling for expected family member count when a family photo is used.
- Add a validation/fallback path so the system does not silently accept an illustration that clearly represents fewer people than expected.
- Keep existing cover-photo upload and guide generation flows compatible when no family photo or no count is available.

## Capabilities

### New Capabilities

- `family-cover-illustration`: Covers family-photo cover prompt construction, expected member preservation, validation, and fallback behavior.

### Modified Capabilities

- None. No main specs exist yet in this repository.

## Impact

- Cover photo upload and preview state in the guide creation frontend.
- Backend cover image prompt construction and image generation utilities.
- Guide generation request metadata for expected family member count.
- Tests for prompt construction, generation fallback, and end-to-end guide generation with a family cover photo.
