## Context

The current wizard already knows selected catalog and custom tourist points, family members, and
child ages. The progressive builder persists an immutable ordered page plan and only generates the
active page when the parent asks. Approved PNGs are later packaged into a private PDF, one image
per page.

The legacy guide engine already contains reusable concepts and utilities for age complexity,
coloring, word search, detail hunt, and free-form painting. The progressive page plan currently contains only
`cover`, `trip_summary`, and `landmark` pages. Its tourist-point metadata keeps only name, city,
and country, so it must retain richer server-resolved context before activity pages can be reliable.

OpenAI's current image documentation distinguishes prompt-only generation from editing one or
more source images. This change keeps the Image API because each page is an explicit immutable
generation attempt. Landmark-bound activities use edits with reference images; the trip-wide
memory page can use generation for its first attempt and editing for revisions.

## Goals / Non-Goals

**Goals:**

- Support any selected catalog or custom tourist point without hard-coded place branches.
- Make all optional activity selection explicit and understandable through visual examples.
- Generate activity artwork that visibly belongs to the selected tourist point and guide style.
- Produce usable, printable activities rather than merely decorative activity-like images.
- Always append one child-writable `Minha melhor memória` page after all tourist-point content and
  one family-consistent `Hora de voltar para casa` page as the final page.
- Preserve the existing page review, regeneration, approval, privacy, cleanup, and PDF contracts.

**Non-Goals:**

- A free-form activity designer.
- A separate activity marketplace or per-child copy of the guide.
- Guaranteed factual enrichment from unconstrained model knowledge.
- Digitally saving what the child writes on the printed guide.
- Replacing the current page-by-page Image API workflow with a conversational Responses API flow.

## Proposed User Journey

1. The parent confirms tourist points.
2. The parent enters family members and child ages.
3. A new `Atividades` step groups the selected points in itinerary order.
4. Each point shows its name, city/country, source image when available, and a grid of visual
   activity examples. No optional activity starts selected.
5. The parent can select up to two activity types per point, or continue with none. The screen
   shows the resulting optional-page count and explains that `Minha melhor memória` and
   `Hora de voltar para casa` are always included.
6. Photo and final review show the selected activities beside their linked point.
7. The progressive builder generates and approves every page in sequence.
8. The existing PDF action packages the approved sequence without special activity-PDF logic.

## Page Sequence

For each newly created builder session, page order is deterministic:

1. `cover`
2. `trip_summary`
3. For each selected tourist point in itinerary order:
   1. `landmark`
   2. zero or more selected `landmark_activity` pages in the parent's selection order
4. exactly one `best_memory` page
5. exactly one `homecoming` page

Example:

```text
cover
summary
landmark-1
activity-landmark-1-coloring
activity-landmark-1-word-search
landmark-2
activity-landmark-2-detail-hunt
best-memory
homecoming
```

The final PDF compositor needs no new layout branch because it already consumes the exact
approved PNG sequence.

## Decisions

### Decision 1: Bind selections to canonical landmark IDs

The frontend submits only a strict list similar to:

```json
[
  {
    "landmark_selection_id": "paris:eiffel-tower",
    "activity_type": "coloring",
    "order": 1
  }
]
```

Allowed optional types are `detail_hunt`, `word_search`, `drawing`, and `coloring`. The client does
not submit landmark names, country, descriptions, prompts, reference URLs, asset paths, or page
IDs. The server resolves every selection ID against the same ordered catalog/custom landmark set
used to build the guide. Unknown, duplicated, orphaned, or unselected point IDs are rejected.

Older drafts default to an empty selection list. When a parent removes a tourist point, the
frontend immediately prunes activity selections linked to it and the backend still validates the
final submitted set.

### Decision 2: Add a dedicated visual frontend step

The new step sits after family details and before the photo step. At that point, landmark identity
and child ages are both available. It uses one expandable section per selected point and activity
cards containing:

- a committed representative preview image labeled `Exemplo`;
- the activity name and a short child-facing example;
- recommended age band and approximate completion time;
- material badges such as pencil or colored pencils;
- `Será adaptada para <nome do ponto>`;
- an accessible checkbox/toggle and selected state.

Preview assets illustrate the product choice only; they are never used as generated guide output.
The step supports mobile, keyboard navigation, screen readers, light/dark themes, and an explicit
`Continuar sem atividades opcionais` path. The review screen shows the exact point-to-activity
mapping and the mandatory memory page.

The initial cost guard is two optional activities per point and eight optional activity pages per
guide. Both limits are shared backend/frontend constants and can be adjusted after real usage data.

### Decision 3: Persist selections in authenticated drafts and form data

`ConversationalGuideContext` stores `landmarkActivitySelections`, restores it from existing owner
drafts, prunes invalid associations, and resets it when route data is reset. Submission adds one
bounded `activity_selections_json` form field. The backend parses it into strict typed records and
stores the normalized selection snapshot in the private builder session.

The idempotency hash includes the normalized selection list so the same key cannot replay a guide
with a different activity plan.

### Decision 4: Resolve a reusable landmark activity context on the server

Every selected point becomes an immutable server-side context containing:

- canonical `selection_id`;
- name, city, and country;
- child-friendly description paragraphs already supplied by catalog/custom-place resolution;
- an optional trusted curiosity;
- `place_id` and sanitized local visual reference when available;
- the matching progressive landmark page ID;
- age complexity derived from the submitted child ages.

Catalog landmark descriptions remain authoritative. Catalog data should gain optional
landmark-specific curiosity copy; until then, a destination curiosity may be used only when it
clearly applies. Custom landmarks use the description already resolved from Places or existing
enrichment. If no supported curiosity is available, the page uses a non-factual observation prompt
instead of asking the model to invent a claim.

The complete resolved context is stored in page metadata so regeneration is reproducible even if
catalog data changes later.

### Decision 5: Enrich tourist-point pages before their activities

Each `landmark` page receives two additional exact-copy fields:

- a concise age-appropriate description;
- one curiosity or safe observation prompt.

The server bounds and normalizes both strings before constructing the image prompt. They are part
of `required_copy`, displayed to the parent during review, and kept stable across attempts.

### Decision 6: Use the best available point reference without imposing generation order

A landmark activity can be generated at any time, including before its associated landmark page.
The server resolves every reference itself and uses the strongest material currently available:

1. a sanitized local source photo/reference when one already exists for the selected place;
2. the selected generated landmark-page attempt, whether or not the parent has approved it yet;
3. the selected current activity attempt for regeneration only.

When none of these visual references exists, the activity uses prompt-only generation from the
immutable server-resolved landmark name, city, country, description, and age complexity. This
fallback preserves the free page-order workflow; later approval of the linked landmark does not
reorder pages or mutate an already generated activity attempt.

No external URL or client path reaches the OpenAI request. Reference order is fixed and tested.
Activity prompts remove every person, family member, readable point-page text, logo, and watermark
unless a future activity explicitly changes that policy.

### Decision 7: Generate usable activity pages, not only visual imitations

Every activity page contains an OpenAI-generated visual layer and finishes as a validated
1024×1536 PNG. Functional content is handled by activity type:

- `coloring`: OpenAI edits the landmark reference into black-and-white child-friendly line art.
  The existing line-art simplifier normalizes it to large closed shapes, clean black lines, white
  background, and no text or people. The final page adds exact heading/instructions and generous
  printable margins.
- `detail_hunt`: the activity specification selects bounded observable details from trusted
  landmark context and the available point references. OpenAI creates the landmark-specific visual layout;
  exact clues and checkboxes are rendered from the validated specification.
- `word_search`: the existing seeded grid generator builds a solvable puzzle from normalized place,
  city, and activity vocabulary. OpenAI creates the decorative landmark vignette/background, while
  code composites the exact grid and word list so letters cannot drift.
- `drawing`: the backward-compatible technical type now represents `Minha pintura`. OpenAI creates
  a point-specific painting-workshop frame, a small landmark vignette, palette, and brushes around
  a large pure-white canvas. Exact painting prompt text and writing lines are composited afterward.

This hybrid still uses the OpenAI API for every activity page while preserving puzzle correctness,
print usability, and exact Portuguese copy. Regeneration may change artwork and framing but must
not silently change the approved activity type, linked point, word-search solution, or mandatory
instructions.

### Decision 8: Always append `Minha melhor memória`

`best_memory` is server-created and never appears as an optional selection. Every new session gets
exactly one page after all tourist points and optional activities, immediately before the closing
page. It contains stable exact copy for:

- `Minha melhor memória`;
- favorite place;
- what the child liked most;
- what the child discovered;
- a large drawing area and a short writing/signature/date area.

The first attempt uses OpenAI generation with the trip title, date, confirmed landmark names, age
complexity, and the established watercolor style. It must not pre-fill the child's answers.
Regeneration edits the selected memory-page attempt. The page is mandatory to approve before PDF
export and remains people-free to maximize writable space.

### Decision 9: Extend the generic page state machine

`GuidePageGenerator` gains explicit activity, memory, and homecoming generation methods. The
builder endpoint dispatches `landmark_activity` by its strict activity subtype, `best_memory`, and
`homecoming` separately. Existing attempt reservation, idempotency, four-version budget,
selection, approval, error recovery, private asset serving, cleanup, and PDF export remain shared.

The UI shows an activity badge and linked landmark in `GuideAssembly`. `Incluir família` remains
available only for `landmark`; activity and memory pages never inherit the current default that
non-landmark pages require family references.

### Decision 10: Keep costs and page counts bounded

The server rejects more than two optional activities for one point, more than eight optional
activity pages, duplicates, and unsupported types before any provider call. The page-generation
quota is recalculated for the expanded maximum page plan and remains owner/IP/concurrency bounded.
No activity image is generated during selection, draft saving, builder-session creation, or page
planning.

Visual examples are static committed assets, so merely exploring activity choices is free.

### Decision 11: Preserve privacy and lifecycle behavior

Activity references, generated artwork, deterministic overlays, and PDFs live in the existing
private owner-scoped builder asset directory. They expire and are deleted with the session or
account. OpenAI receives only the server-resolved landmark references needed for the active page;
activity pages do not receive the family photo or approved cover.

### Decision 12: Backward compatibility applies at draft and session boundaries

Drafts without activity selections restore as `[]`. Existing persisted builder sessions keep their
already-materialized page list and are not mutated to insert a memory page. Only sessions created
after the feature use the expanded plan.

### Decision 13: Treat coloring pages as printable worksheets, not detailed line-art posters

The model generates only the recognizable landmark drawing. It receives an age-band-specific
complexity contract: preschool pages use very few large closed regions, early-reader pages retain
only the landmark's signature features, and older-child pages may add moderate detail without
micro-patterns, shading, or hatching. Every version remains people-free and must reserve the
heading area.

Trusted code then fits the simplified drawing inside a bounded illustration region and composites
the exact instruction `Agora é a vez de colorir <ponto turístico> do seu jeito.` near the top of
the page. The instruction is derived from the server-resolved landmark name rather than accepted
from the client or delegated to the image model. Final monochrome validation requires generous
white space so overly dense artwork fails instead of becoming a frustrating coloring activity.

### Decision 14: Finish every new guide with a family-consistent homecoming page

Every new builder session appends exactly one mandatory `homecoming` page after
`best_memory`. Its OpenAI artwork uses the original family photo and approved cover as fixed
identity references, depicts the same family preparing to return home in a warm airport or travel
terminal scene, and never invents readable signs, airline brands, flags, or a destination-specific
home country.

The model creates only the decorative illustration. Trusted code composites the exact Portuguese
title and closing copy, plus a large lined field labeled
`Uma coisa que quero contar quando chegar em casa:`. The page remains part of the normal generate,
regenerate, approve, completion, cleanup, and one-image-per-PDF-page lifecycle. Existing persisted
sessions are not replanned, preserving backward compatibility.

### Decision 15: Retry temporary limits without duplicating a generation

The API distinguishes the application's own rate/concurrency controls from provider-side OpenAI
limits. Short OpenAI `429`/`5xx` responses receive a bounded exponential backoff with jitter in the
backend. A long OpenAI `Retry-After` becomes a structured temporary API error instead of keeping an
HTTP request open for minutes.

The frontend preserves `code`, `scope`, and `Retry-After`, then performs at most three automatic
retries after the initial request. Every attempt reuses the same idempotency key, keeps its waiting
state attached to the requested page, and does not prevent other pages from generating. Server
delays take precedence; otherwise the fallback schedule grows from seconds to minutes. Daily quota
exhaustion and permanent errors never retry automatically, and unmounting the review cancels its
pending timers and requests.

### Decision 16: Replace free drawing with a blank-canvas painting activity

The fourth optional card is presented to parents and children as `Minha pintura`, not
`Desenhe sua versão`. It offers a clean canvas where the child creates a painting inspired by the
selected tourist point. The generated border may contain a small recognizable point vignette,
palette, and brushes, but the central canvas must remain pure white and free of model-created
sketches, tracing guides, shading, or text.

This remains intentionally distinct from `Página para colorir`: coloring supplies deterministic
black line art ready to fill, while painting starts with a blank canvas. Trusted code renders the
title, point name, exact instruction, `Título da minha pintura`, and date field. The serialized
activity type remains `drawing` so existing drafts, builder sessions, API clients, and page IDs
continue to load without migration; only its product meaning and visible copy change.

## Validation Strategy

### Backend and content tests

- Normalize valid catalog and custom-place selections without hard-coded names.
- Reject unknown, unselected, duplicated, over-limit, and malformed activity records.
- Prove point description/curiosity fallback never invents unsupported facts.
- Prove page order for no optional activities, several points, several activity types, and custom
  landmarks.
- Prove every new session has exactly one `best_memory` page followed by exactly one final
  `homecoming` page.
- Prove old persisted sessions still load unchanged.

### Provider and image tests

- Assert endpoint, model, prompt contracts, multipart reference ordering, people-free constraints,
  and revision inputs for each page kind.
- Assert coloring output is black-and-white, printable, correctly sized, and retains a recognizable
  landmark composition, age-aware simplicity, generous white space, and the exact dynamic
  `Agora é a vez de colorir <ponto turístico> do seu jeito.` instruction.
- Assert word-search grids and solutions survive compositing exactly.
- Assert painting/memory pages preserve minimum blank writable areas.
- Assert the homecoming prompt preserves family identity and the deterministic compositor keeps
  the closing copy and writable area exact.
- Assert invalid, oversized, malformed, or wrong-size provider output creates no attempt.
- Assert OpenAI temporary limits back off, expose long `Retry-After` values, and leave the same
  idempotency key reusable without consuming an attempt.

### Frontend and browser tests

- Activity examples are visual, accessible, point-specific, and unselected by default.
- Selection limits, pruning after point removal, draft restore/reset, back navigation, mobile
  layout, and review summary behave correctly.
- A family can select different activities for two points, approve the entire ordered sequence,
  retry one failed activity generation, approve the mandatory memory page, and download the PDF.
- Continuing with no optional activities still creates and requires the memory page.
- Completion and PDF export also require approval of the final homecoming page.
- Temporary-limit feedback remains page-local, visible, bounded, and compatible with parallel page
  generation.

### PDF and live validation

- Export a mixed approved sequence and render every PDF page to prove exact ordering and full-page
  coverage.
- Run one paid low-quality OpenAI smoke using a custom, non-catalog tourist point for coloring and
  visually confirm recognizable architecture, no people/text, and usable coloring areas.
- Run one activity-page smoke for writable space and exact copy. Paid smoke tests remain manual and
  reuse the existing `.env` key without logging it.

## Risks / Trade-offs

- More optional pages increase cost and review time. Explicit selection, preview assets, page-count
  feedback, and strict caps make that trade-off visible before generation.
- Image models can distort factual details, letters, and blank space. Server-resolved references,
  deterministic overlays, type-specific validation, and explicit approval reduce the risk.
- Obscure custom places may lack a trustworthy image or curiosity. The approved point page remains
  a fallback visual anchor, and unsupported facts become observation prompts rather than invented
  claims.
- A hybrid renderer is more work than asking OpenAI for a complete puzzle image, but it is necessary
  for solvable word searches and reliable printable fields.
- Static activity previews are representative, not exact previews of the final place-specific
  image. The UI must label them clearly and say which point the generated page will use.

## OpenAI Documentation Basis

- Image generation and editing guide: https://developers.openai.com/api/docs/guides/image-generation
- GPT Image prompting guide: https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide

The official guide recommends the Image API for one-prompt single-image generation/editing and
supports edits using source images. The prompting guide emphasizes explicitly separating what must
stay invariant from what may change, which maps to landmark identity, activity correctness, and
revision constraints in this design.
