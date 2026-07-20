## Why

Optional activities already exist, but parents must choose them in an earlier wizard screen before
they can see the real ordered guide. In the final page-building experience, the activity pages are
mixed into a plain page list without a dedicated catalog, full-page examples, or a clear way to add
an activity where it makes the most sense in the child's journey.

The final builder should make optional activities discoverable at the moment the parent can see the
whole guide. Parents need to compare realistic examples, add an activity for a specific tourist
point, and place its page visually without confusing generation order with final PDF order.

## What Changes

- Add an `Adicionar atividades` action to the final page-building experience in step 6/6.
- Open an accessible activity panel with a realistic full-page example for each supported activity,
  its child age, estimated duration, materials, and a larger preview.
- Let the parent choose the linked tourist point and add the activity without generating an image.
- Add an ordered guide outline that shows every page as a block and every legal insertion slot.
- Let the parent drag an optional activity block to a legal slot or choose the equivalent
  `Inserir depois de` / move controls for touch and keyboard use.
- Keep cover, summary, destination, tourist-point, memory, and homecoming pages in their mandatory
  relative order. An activity defaults to immediately after its linked tourist point and can never
  be placed before that point or after the mandatory closing section.
- Persist additions, removals, and placements immediately on the server. The stored order, not the
  order in which pages are generated, remains the exact PDF order.
- Allow layout edits while unrelated pages are generating, without cancelling or duplicating their
  OpenAI requests.
- Invalidate a cached final PDF whenever the page set or order changes.
- Preserve the existing activity limits: at most two optional activities per tourist point and
  eight per guide.

## Capabilities

### New Capabilities

- `guide-activity-catalog-panel`: Final-builder activity discovery with realistic examples,
  landmark assignment, add/remove controls, and clear cost-free-before-generation behavior.
- `guide-page-layout-editing`: Owner-scoped mutation of optional activity pages and their positions,
  with drag, keyboard, and mobile placement controls backed by a canonical server order.

### Modified Capabilities

- `landmark-activity-selection`: Optional activities may be selected in the earlier wizard or added
  later from the final builder, while preserving the same type, landmark, duplicate, and quota rules.
- `progressive-guide-page-generation`: A builder session can gain, lose, or reposition optional
  activity pages without changing generation/approval order or mutating existing attempts.
- `guide-content-generation`: PDF export consumes the latest approved canonical page order and
  invalidates older cached output after a structural edit.

## Impact

- `GuideAssembly` layout, responsive activity drawer, page outline, previews, local optimistic state,
  and accessible drag/move interactions.
- Static example assets and activity catalog metadata.
- Builder session persistence, public response revision fields, activity-page construction helpers,
  and cached PDF lifecycle.
- New authenticated builder endpoints for adding, removing, and moving optional activity pages.
- Backend, frontend, API-contract, concurrency, accessibility, browser, PDF-order, and deployment
  validation.

## Non-Goals

- Reordering cover, summary, destination, tourist-point, `Minha melhor memória`, or homecoming pages.
- Generating an activity merely because the parent opened the catalog or clicked `Adicionar`.
- Accepting landmark names, prompts, image paths, arbitrary page IDs, or an entire page plan from the
  browser.
- Removing the existing earlier activity step in this first iteration; it remains a useful shortcut
  and feeds the same canonical builder plan.
- Adding new activity types, changing activity artwork generation, or creating a general-purpose
  page designer.
