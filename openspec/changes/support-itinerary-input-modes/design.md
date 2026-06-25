## Context

The current structured destination flow asks for each destination directly. Feedback suggests a second path: let users speak freely about a route, then ask specific questions like how many days they will stay in each place and what order the itinerary follows. Separately, some users may want AI to suggest route options.

## Goals / Non-Goals

**Goals:**

- Support both known itinerary and AI-suggested itinerary modes.
- Convert either mode into the same structured destination list used by the rest of the product.
- Ask follow-up questions only for missing or ambiguous fields.
- Keep attractions, preferences, family details, cover, review, and guide generation downstream unchanged where possible.

**Non-Goals:**

- Replace the existing structured destination entry UI.
- Build a full travel booking or transport optimization engine.
- Guarantee that AI-suggested itineraries are exhaustive or bookable.

## Decisions

- Treat structured destinations as canonical. Freeform and AI suggestion modes are input helpers that must produce editable destination records.
- Add a mode selector before destination capture. Known itinerary defaults to direct structured entry; freeform can prefill records and ask follow-ups.
- Use a missing-field model for follow-up prompts. The system should detect missing place, timing, duration, and order, then request only what is absent.
- Make AI suggestions editable before proceeding. Users can accept, remove, reorder, or edit destinations before attraction discovery.

## Risks / Trade-offs

- More choices can slow onboarding -> Keep the default path direct and make modes visually compact.
- AI suggestions may be low quality -> Require review/editing before suggestions become canonical destinations.
- Parsing freeform routes can be ambiguous -> Use targeted follow-up questions rather than guessing silently.
