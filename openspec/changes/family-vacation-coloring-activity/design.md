## User Journey

1. A parent sees `Família de férias para colorir` beside the other optional activities.
2. The card shows a synthetic full-page example and explains that the family photo guides the
   characters while the chosen point guides the vacation scene.
3. Adding the activity creates a ready page without an OpenAI request.
4. When the parent clicks `Gerar página`, the backend privately supplies the sanitized family photo,
   an approved cover if one exists, available landmark references and the selected prior attempt.
5. The provider creates artwork only; trusted code adds the exact page copy and validates printable
   line-art density.

## Contracts

The persisted activity type is `family_coloring`. It remains landmark-bound so ordering, quotas,
removal and PDF export reuse the existing safe structural model. The page ID follows the existing
stable pattern: `activity-{itinerary_order}-family-coloring`.

Required copy:

- `Família de férias para colorir`
- the server-owned family title
- the canonical landmark name
- `Agora é a vez de colorir a aventura da sua família em {landmark}.`

## Reference And Privacy Model

The raw photo is mandatory at generation time but never copied to public metadata. An approved cover
is optional and improves continuity without introducing a dependency. Local landmark art and the
approved landmark page are optional. A selected activity attempt is only a revision reference.

The prompt assigns every supplied image a role and requires the family count, age relationships,
recognizable hairstyles, glasses and major accessories to remain consistent. It requests an original
visual language described by traits, never by a living artist or brand name.

## Artwork And Composition

The provider output contains no text and reserves the top area. It must be pure black and white with
smooth bold contours, comfortably large closed shapes, low visual density and no gray, color,
hatching, micro-patterns or filled black masses. The deterministic compositor reuses the proven
line-art layout and density validation, then adds exact Portuguese copy.

## Failure Behavior

- Missing family photo: return the existing bounded family-photo unavailable error before provider
  invocation.
- Missing cover or landmark page: continue with the remaining safe references.
- Invalid or overly dense line art: fail atomically without consuming a completed attempt.
- Regeneration: preserve family-reference invariants while applying bounded user feedback.

## Validation

- Type/normalization and catalog tests cover the fifth activity.
- Prompt tests assert family-reference roles, family-count preservation, original-style constraints
  and absence of named-artist language.
- Generator tests assert private family-photo use, optional references, exact dispatch, temporary
  cleanup and compositor output.
- API tests prove add-without-generation and generation without an approved cover.
- Frontend tests cover the example asset and copy; build/bundle checks protect deployment.
