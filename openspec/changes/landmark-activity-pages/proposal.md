## Why

The progressive guide currently ends after the illustrated tourist-point pages. That makes the
guide useful to the parents who planned the trip, but it does not yet give the child enough to do,
observe, complete, and preserve as a personal travel memory.

Activity pages cannot depend on a fixed catalog such as the Eiffel Tower or on knowing a country
in advance. They must bind to the exact catalog or custom tourist point selected by the parent,
resolve its location and visual identity on the server, and remain correct when the trip contains
previously unknown places.

## What Changes

- Add a dedicated visual activity-selection step after family details, when both the selected
  tourist points and child ages are already known.
- Show representative preview artwork for every activity type, not description-only choices.
- Let the parent explicitly select zero or more optional activities for each tourist point.
- Start with four optional landmark-bound activities: detail hunt, word search, drawing prompt,
  and coloring page.
- Add one mandatory `Minha melhor memória` page after every tourist point and its selected
  activities.
- Add one mandatory `Hora de voltar para casa` closing page after `Minha melhor memória`, with the
  same family established on the approved cover and a writable homecoming reflection prompt.
- Add a short child-friendly description and a safe curiosity or observation prompt to every
  tourist-point page.
- Generate the visual layer of every activity page through the configured OpenAI Image API and
  reuse the approved tourist-point page or a sanitized landmark reference for place fidelity.
- Make every coloring page a genuinely child-usable black-and-white worksheet, with age-aware
  visual complexity and the exact point-specific phrase
  `Agora é a vez de colorir <ponto turístico> do seu jeito.` rendered by trusted code.
- Keep rule-bound content such as a word-search grid deterministic and validated, compositing it
  onto the OpenAI-generated activity artwork so the puzzle remains solvable.
- Reuse the current generate, regenerate, approve, gallery, and final PDF workflow. Every approved
  activity PNG becomes one PDF page in the existing sequence.

## Capabilities

### New Capabilities

- `landmark-activity-selection`: Parent-facing visual selection, draft persistence, validation,
  and age-aware optional activity configuration per selected tourist point.
- `landmark-activity-page-generation`: OpenAI-backed, tourist-point-specific activity pages plus
  the mandatory trip-memory and homecoming pages.

### Modified Capabilities

- `progressive-guide-page-generation`: The ordered page plan includes selected activity pages, a
  mandatory memory page, and a mandatory closing page before PDF export.
- `openai-guide-page-art`: Activity pages can edit server-resolved landmark references while
  preserving the exact selected place and removing people when required.
- `guide-content-generation`: Tourist-point pages gain child-friendly description and curiosity
  copy resolved from trusted landmark context.

## Impact

- Frontend wizard step count, state, draft persistence, review summary, and activity preview
  assets.
- Guide-builder form contract, strict activity validation, persisted page metadata, and page plan.
- OpenAI page-generator protocol, prompts, reference resolution, activity-specific validation,
  and request quotas.
- Existing word-search and coloring-lineart utilities, which can be reused instead of rebuilt.
- Builder API, browser lifecycle, PDF sequence, cleanup, privacy, and cost-control tests.

## Non-Goals

- Automatically selecting or generating optional activities without an explicit parent choice.
- Shipping memory-card cutting sheets, mazes, quizzes, or answer-book appendices in the first
  activity release.
- Trusting client-provided landmark names, prompts, filesystem paths, or page order.
- Asking the image model to invent factual curiosities or to create an unvalidated puzzle grid.
- Retrofitting already-created builder sessions; the new page plan applies to new sessions.
