## Why

Families may want meal suggestions near the places suggested on the map, but restaurant recommendations are an add-on idea rather than core guide content. The product needs a clear paid-extra flow so restaurant tips can be offered without changing the base guide experience.

## What Changes

- Add an optional paid extra for family-friendly restaurant recommendations near selected map places.
- Price and label the extra separately from the base guide, initially at BRL 29.90.
- Generate restaurant suggestions only when the extra is selected or purchased.
- Keep restaurant recommendations linked to nearby attractions or itinerary areas for practical use.

## Capabilities

### New Capabilities

- `restaurant-recommendations-extra`: Covers add-on selection, pricing contract, restaurant discovery near selected places, and guide rendering for the extra.

### Modified Capabilities

- None. No main specs exist yet in this repository.

## Impact

- Add-on/pricing UI in the guide creation or checkout flow.
- Backend request contract for optional paid extras.
- Restaurant discovery provider or prompt logic.
- Guide rendering for restaurant recommendations when included.
- Tests for opt-in behavior, pricing, recommendation locality, and base guide exclusion.
