## Why

Attraction suggestions can feel too narrow, missing family-friendly categories such as parks, squares, theaters, and other local places. Families need enough diverse options to choose places that match their travel style before the guide is generated.

## What Changes

- Expand attraction discovery to request and return a broader set of family-friendly place categories.
- Group or label suggestions by category so users can scan parks, squares, museums, theaters, stores, outdoor options, and similar programs.
- Require a minimum useful number of options per destination when source data is available.
- Preserve user control over which suggestions enter the final guide.

## Capabilities

### New Capabilities

- `expanded-attraction-options`: Covers broader attraction category discovery, categorized presentation, option counts, and user selection behavior.

### Modified Capabilities

- None. No main specs exist yet in this repository.

## Impact

- Attraction discovery prompt/API request construction.
- Place recommendation normalization and category metadata.
- Attraction selection UI and tests.
- Backend/frontend tests for option diversity and selected-place preservation.
