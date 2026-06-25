## Context

The existing flow can suggest attractions, but feedback indicates the option set feels too limited. The product should deliberately ask for broader categories and present enough alternatives for families to make meaningful choices.

## Goals / Non-Goals

**Goals:**

- Increase variety across family-friendly categories.
- Make categories visible enough for quick scanning and selection.
- Keep selected attractions as the only confirmed guide content.
- Avoid changing the final guide unless the user selects new places.

**Non-Goals:**

- Guarantee real-time opening hours or ticket availability.
- Replace map search or external place data with a custom POI database.
- Automatically include every suggested place in the guide.

## Decisions

- Add category targets to discovery requests. The backend should ask for a mix including parks, squares, theaters, museums/art, outdoor activities, shopping/local stores, and flexible family programs.
- Normalize each suggestion with a category, destination, title, short reason, and optional map metadata.
- Use minimum option targets as best-effort. If a destination has limited data, the UI can show fewer options with no fake padding.
- Keep user selection explicit. Expanded options improve choice but do not bypass review.

## Risks / Trade-offs

- More options can overwhelm users -> Group by category and keep selected state clear.
- Source data may be sparse for small destinations -> Use best-effort counts and communicate when fewer options are found.
- Broad prompts can reduce relevance -> Include family preferences, child ages, trip pace, and destination duration in discovery context.
