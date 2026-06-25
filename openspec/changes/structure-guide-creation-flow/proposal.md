## Why

The guide creation flow currently asks for destinations as one freeform text block, keeps itinerary preferences hidden inside the attractions step, and captures children without ages. This makes the input harder to complete, weakens itinerary personalization, and prevents the generated guide from reliably adapting activity complexity to the family.

## What Changes

- Replace the first freeform destination prompt with repeatable structured destination entries: where the family is going, when, and for how many days.
- Add a fixed preferences step immediately after destinations for trip pace and activity/program categories that match the family.
- Update child collection to capture each child's name and age.
- Pass children ages into itinerary discovery/recommendation so suggested stops and activities can use age as a personalization signal.
- Formalize the generated guide content order: welcome, visual itinerary summary, destination sections with activities, and final checklist/questions.
- Diversify guide activities across destinations, including coloring, word search, spot-the-difference, detail hunt, prompts, drawing, and checklist-style activities.
- Adapt activity complexity to the children's ages while keeping activities usable for mixed-age families.
- Preserve the existing review, map, landmark selection, cover photo, and PDF generation paths while updating their data contracts.

## Capabilities

### New Capabilities

- `guide-creation-flow`: Covers the multi-step guide creation wizard, structured destination entry, itinerary preferences, family details, and review data flow.
- `guide-content-generation`: Covers the PDF/HTML guide structure, destination activity plan, activity diversity, and age-aware activity complexity.

### Modified Capabilities

- None. No main specs exist yet in this repository.

## Impact

- Frontend state and UI:
  - `frontend_atual/apps/web/src/contexts/ConversationalGuideContext.jsx`
  - `frontend_atual/apps/web/src/pages/CreateGuidePage.jsx`
  - destination, preferences, attractions, family details, review components
- Frontend API contract:
  - `frontend_atual/apps/web/src/utils/minerva-api.js`
  - itinerary discovery payloads must include structured preferences and child ages.
- Backend models and guide building:
  - `src/minerva_travel/models.py`
  - `src/minerva_travel/guide_builder.py`
  - `src/minerva_travel/templates/guide.html`
  - `src/minerva_travel/templates/styles.css`
- Tests:
  - Python model, itinerary, guide builder, app/render tests.
  - Frontend tool tests covering wizard order, structured inputs, payload serialization, and review/generation contracts.
