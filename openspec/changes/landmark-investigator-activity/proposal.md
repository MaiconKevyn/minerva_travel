## Why

The optional activities currently give every child the same task. Families also need a collaborative
investigation in which every registered child receives a distinct, age-appropriate mission tied to
the tourist point they are visiting.

## What Changes

- Add `investigator` as a sixth optional landmark-bound activity named `Investigador`.
- Generate one concise clue and one mission for every registered child, preserving child order and
  adapting observation, reading and writing demands to each age.
- Use only the persisted tourist-point context and robust observable features so a mission remains
  useful during the real visit without asserting an unverified temporary exhibit or access rule.
- Generate a family-consistent, text-free visual layer through OpenAI, then apply all functional
  Portuguese copy and completion boxes with deterministic code.
- Show a reviewed synthetic full-page example in the activity panel.
- Keep the existing two-activities-per-landmark and eight-per-guide limits.

## Impact

- Optional-activity contracts, page metadata and progressive-builder dispatch.
- Structured OpenAI mission generation, family/landmark reference assembly and deterministic page
  composition.
- Frontend activity catalog, preview asset and responsive card grid.
- Backend, frontend, generation, compositor and browser tests.

## Non-Goals

- Producing a multi-page detective booklet for one tourist point.
- Claiming that a temporary artwork, room or attraction will be available on the visit date.
- Asking a child to separate from adults, touch exhibits, cross barriers or break venue rules.
- Rendering model-generated functional text directly into the final page.
