## 1. Contracts And Tests

- [x] 1.1 Add frontend tests for itinerary mode selection and canonical structured destination output.
- [x] 1.2 Add parser tests for freeform route text with missing duration, missing order, and complete structured output.
- [x] 1.3 Add API tests for AI-suggested route options and acceptance into destination records.

## 2. Destination Flow Implementation

- [x] 2.1 Add itinerary mode state to the guide creation context.
- [x] 2.2 Add a compact mode selector to the destination step.
- [x] 2.3 Implement freeform route input and missing-field follow-up prompts.
- [x] 2.4 Implement AI-suggested route option loading, selection, edit, and rejection behavior.
- [x] 2.5 Ensure confirmed route data updates the existing structured destination list.

## 3. Backend And API Integration

- [x] 3.1 Add or extend itinerary suggestion endpoint support for route-level suggestions.
- [x] 3.2 Normalize accepted suggested routes into the same destination payload used by attraction discovery.
- [x] 3.3 Preserve compatibility for existing direct structured destination requests.

## 4. Verification

- [x] 4.1 Run frontend flow and utility tests for destination mode behavior.
- [x] 4.2 Run backend tests for route suggestion and parsing behavior.
- [x] 4.3 Run `openspec validate support-itinerary-input-modes --strict`.
