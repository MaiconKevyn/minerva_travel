## Reference Findings

The supplied Louvre reference uses a mission briefing, child-specific detective roles, short clues,
different actions for different ages and a completion marker. The product will condense those useful
elements into one printable page per selected tourist point so it fits the existing guide assembly,
ordering and PDF export model.

## User Journey

1. A parent opens the activity panel and sees `Investigador` with a real synthetic example.
2. The parent adds it to any selected tourist point and may position it like every other activity.
3. The builder immediately creates the page slot without calling OpenAI or requiring another page.
4. On `Gerar página`, structured text generation creates exactly one clue and mission for every
   registered child, in the original family order and with age-appropriate complexity.
5. Image generation uses the private family photo first, an approved cover when available, and
   available landmark references to create only the visual layer.
6. Trusted code adds the exact title, landmark name, child names, clues, missions and printable
   completion boxes. The approved result remains in its configured guide position.

## Contracts

The persisted activity type is `investigator`. The stable page ID is
`activity-{itinerary_order}-investigator`. The page is optional, landmark-bound and consumes one of
the existing activity slots.

Required static copy:

- `Investigador`
- the canonical landmark name
- `Cada criança tem uma missão secreta. Observem com atenção e trabalhem em equipe!`
- one `Missão de {child}` heading and one empty `Concluí` checkbox per registered child

The supported child count is the guide contract of one to ten. Mission cards use one column for one
child and two columns otherwise, with up to five rows.

## Mission Generation

The Responses API receives the canonical landmark name, city, country, child-safe description,
curiosity and ordered child names/ages. A strict JSON schema returns exactly one bounded clue and one
bounded mission per child. Server validation rejects missing, duplicate, reordered or renamed
children and overlong content.

Age bands guide complexity: ages zero to five use pointing, matching, counting or imitation; ages
six to eight use observation, comparison and short answers; ages nine to seventeen may use public
labels, inference and a short written observation. All tasks remain possible beside an adult and
must respect barriers, venue rules and accessibility.

## Visual And Privacy Model

The raw sanitized family photo is mandatory at generation time and remains private. An approved
cover, local landmark reference, approved landmark page and selected prior attempt are optional.
The prompt gives every input a single role, preserves the complete family and keeps the page's top
and lower mission regions free from model text and important visual details.

The provider never renders the title, names, clues, missions, checkboxes, signs, logos or page
numbers. The deterministic compositor owns all functional text and geometry.

## Failure Behavior

- Missing family photo: fail before provider invocation with the existing bounded error.
- Missing cover or landmark page: continue with remaining references.
- Invalid mission JSON or child mapping: fail atomically; no completed attempt is persisted.
- HTTP 429 or temporary provider failure: reuse the current bounded retry and durable retry metadata.
- Invalid artwork or text overflow: fail atomically and retain the prior approved attempt.

## Validation

- Contract tests cover the sixth activity and unchanged quotas.
- Mission tests cover one to ten children, age adaptation, exact ordering and malformed model output.
- Prompt/generator tests cover structured text, family-first references, optional dependencies and
  temporary-file cleanup.
- Compositor tests render representative one-, two- and ten-child pages at 1024x1536.
- Frontend and browser tests cover the card, example dialog, image loading and accessible controls.
