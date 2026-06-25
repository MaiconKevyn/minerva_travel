## Why

Some families arrive with a defined route while others want help turning an open trip idea into a usable itinerary. The guide creation flow needs to support both modes while still collecting the structured information required for useful AI suggestions.

## What Changes

- Add an itinerary input mode that lets users choose between entering a known route and requesting AI suggestions.
- Keep freeform itinerary input available, then ask targeted follow-up questions for missing days, order, and destination details.
- In suggestion mode, collect trip constraints and generate editable route options before attraction selection.
- Preserve structured destination entries as the canonical data used by downstream itinerary discovery and guide generation.

## Capabilities

### New Capabilities

- `itinerary-input-modes`: Covers known-itinerary input, AI-suggested itinerary input, follow-up questions, and conversion into structured destinations.

### Modified Capabilities

- None. No main specs exist yet in this repository.

## Impact

- Destination step UI and state.
- Itinerary parsing and suggestion endpoints or frontend API utilities.
- Destination serialization used by attraction discovery and guide generation.
- Tests for mode selection, follow-up prompts, parsing, and route suggestion acceptance.
