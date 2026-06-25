## 1. Discovery Contract And Tests

- [x] 1.1 Add tests for normalized attraction options with destination, title, category, and stable selection identity.
- [x] 1.2 Add tests proving discovery can return parks, squares, theaters, museums or art, outdoor programs, and local stores when available.
- [x] 1.3 Add tests proving selected attractions, not all suggestions, enter guide generation payloads.

## 2. Backend Recommendation Logic

- [x] 2.1 Extend attraction discovery prompts or providers with broader category targets.
- [x] 2.2 Normalize returned suggestions with category metadata and destination ownership.
- [x] 2.3 Implement best-effort minimum option targets without duplicating or inventing places.
- [x] 2.4 Use trip preferences, pace, destination duration, and child ages to rank or filter options.

## 3. Frontend Selection UI

- [x] 3.1 Display attraction categories through labels, filters, or grouped sections.
- [x] 3.2 Preserve existing select/deselect behavior while handling larger option sets.
- [x] 3.3 Update review to summarize selected attractions with category context.

## 4. Verification

- [x] 4.1 Run backend attraction recommendation tests.
- [x] 4.2 Run frontend attraction selection and guide payload tests.
- [x] 4.3 Run `openspec validate expand-attraction-options --strict`.
