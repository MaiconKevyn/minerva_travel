## 1. Frontend Data Contracts And Tests

- [x] 1.1 Add frontend utility tests for structured destination records, including serialization to the existing destination summary string.
- [x] 1.2 Add frontend utility tests for child records, including deriving child names and child ages from `{ name, age }` records.
- [x] 1.3 Update `tools/create-guide-flow.test.js` to require six wizard steps in the order destinations, preferences, attractions, family details, cover photo, review.
- [x] 1.4 Add a frontend test that verifies itinerary discovery payloads include structured destination context, pace, program categories, and child ages when ages are available.
- [x] 1.5 Add a frontend test that verifies review/generation payloads preserve selected attractions and child name/age data.

## 2. Frontend Wizard Implementation

- [x] 2.1 Add structured `destinationsList` state and helper selectors to `ConversationalGuideContext`.
- [x] 2.2 Replace the primary freeform destination UI in `Step3Destination` with repeatable destination entries for place, timing, and days.
- [x] 2.3 Implement add/remove destination behavior while preventing removal of the final destination.
- [x] 2.4 Extract pace and program category controls from `Step4Attractions` into a dedicated preferences step component.
- [x] 2.5 Update `CreateGuidePage` progress and routing to six steps.
- [x] 2.6 Update `Step4Attractions` so it focuses on attraction loading, map actions, and selection, using preferences from context.
- [x] 2.7 Update family details UI so every child row captures name and age with validation.
- [x] 2.8 Update review UI to summarize destinations, preferences, children with ages, responsible adults, cover photo, and selected attractions.

## 3. Frontend API Payloads And Compatibility

- [x] 3.1 Update `minerva-api.js` helpers to serialize structured destinations for existing discovery and parsing endpoints.
- [x] 3.2 Update attraction discovery calls to send selected pace, program categories, destination duration data, and `children_ages` when available.
- [x] 3.3 Update PDF generation form data to include optional child ages without breaking current child-name submission.
- [x] 3.4 Ensure back navigation and destination edits reset stale parsed attractions, selected landmarks, and recommendations only when relevant structured destination fields change.

## 4. Backend Models And Generation Contract

- [x] 4.1 Add optional child age support to `GuideRequest` or an adjacent guide context model while preserving name-only request compatibility.
- [x] 4.2 Update `/api/generate` and `/generate` form handling to accept optional child age data.
- [x] 4.3 Add backend tests proving guide generation succeeds with child ages and still succeeds without child ages.
- [x] 4.4 Add backend tests proving itinerary recommendation behavior still accepts and uses `children_ages`.

## 5. Guide Activity Planning

- [x] 5.1 Add guide activity model types for coloring, word search, spot-the-difference, detail hunt, drawing, short prompt, and checklist.
- [x] 5.2 Implement deterministic age-band selection using the youngest child as the baseline and a family-friendly fallback when ages are missing.
- [x] 5.3 Implement activity rotation so guides with at least three activities use at least two activity types.
- [x] 5.4 Build an activity plan in `build_guide_context` for selected destinations and landmarks.
- [x] 5.5 Add guide builder tests for single-destination and multi-destination activity plans.
- [x] 5.6 Add tests for activity complexity bands: ages 3-5, 6-8, 9-12, mixed ages, and missing ages.

## 6. Guide Rendering

- [x] 6.1 Update `guide.html` to render welcome, visual summary, destination activity sections, and final checklist/questions from the planned guide context.
- [x] 6.2 Add CSS for new activity layouts without disrupting existing cover, summary, landmark, coloring, and credits pages.
- [x] 6.3 Add render tests that assert preview HTML includes the planned sections in the expected order.
- [x] 6.4 Add PDF generation tests proving a guide with child ages returns a download URL.

## 7. Verification

- [x] 7.1 Run Python tests for models, itinerary, guide builder, app, PDF, and related generation paths.
- [x] 7.2 Run frontend node tests for utilities and tool-level flow checks.
- [x] 7.3 Run frontend lint or build if available in the local environment.
- [x] 7.4 Run `openspec validate structure-guide-creation-flow --strict` and fix any validation issues.
- [x] 7.5 Review the final diff to ensure only the intended flow, model, content, and test files changed.
