## Context

The current frontend wizard starts with `Step3Destination`, which collects one freeform text field and stores it as `destination` in `ConversationalGuideContext`. `Step4Attractions` then auto-runs itinerary discovery and also contains a hidden preference setup for days, pace, and interests. Family details are collected later in `EnhancedStep5FamilyDetails`, where children are stored as names only.

The backend already has itinerary request models that accept `children_ages`, and the PDF pipeline already renders cover, visual route summary, destination pages, activity-like sections, coloring pages, and closing content. The missing pieces are structured collection in the frontend, passing age data through the contracts, and formalizing the PDF content as an activity plan instead of relying only on repeated hard-coded template sections.

## Goals / Non-Goals

**Goals:**

- Deliver all product feedback in one coherent change.
- Replace the primary destination freeform prompt with repeatable structured destination entries.
- Make trip preferences a mandatory visible step after destinations.
- Capture child ages and use them for itinerary and guide content personalization.
- Keep attraction suggestions as a complement to the user's known trip details.
- Formalize generated content order and diversify activity types by age.
- Preserve existing API endpoints, map flow, attraction selection, cover upload, review, and PDF generation where practical.
- Add focused tests for wizard order, data serialization, itinerary payloads, guide activity planning, and rendered output.

**Non-Goals:**

- Building a full date-range calendar or booking itinerary manager.
- Removing attraction suggestions or Google Places discovery.
- Replacing the visual design system.
- Adding new external services or dependencies.
- Conducting user research inside this change.
- Implementing a fully dynamic puzzle generator for every possible activity type; deterministic templates are acceptable for this iteration.

## Decisions

### Decision 1: Use one OpenSpec change with two capabilities

This change stays as one OpenSpec proposal because the feedback forms one user journey: structured input feeds preferences, preferences and child ages feed suggestions, and all of that shapes the generated guide. Splitting into separate changes would create unnecessary sequencing friction.

Alternative considered: split into `restructure-guide-input-flow` and `add-age-aware-guide-content`. This would be cleaner for phased delivery but would delay the main value: age-aware content requires child ages, and content structure depends on destination structure.

### Decision 2: Store structured destinations while preserving a serialized destination summary

Add a `destinationsList` state to `ConversationalGuideContext` with records like:

```js
{
  id: string,
  place: string,
  timing: string,
  days: number
}
```

Keep `destination` as a derived or compatibility string for existing APIs that currently expect one destination description. This avoids a broad backend rewrite during the first implementation pass while allowing the UI and tests to reason over structured data.

Alternative considered: change `/api/itinerary/discover` to accept only structured destinations immediately. That is cleaner long term, but it expands the backend migration and risks breaking existing callers. The safer path is to serialize structured input for current endpoints and add backend structured support only where needed.

### Decision 3: Extract trip preferences into a dedicated wizard step

Move pace and program category controls out of `Step4Attractions` and into a new preferences step after destinations. `Step4Attractions` should focus on loading, displaying, mapping, and selecting attractions.

Alternative considered: keep preferences hidden behind "Sugerir roteiro com dias e categorias." That preserves current code but conflicts with the feedback that these fields should always appear after destination insertion.

### Decision 4: Represent children as objects and derive legacy strings

Store children as records:

```js
{
  id: string,
  name: string,
  age: number
}
```

For existing display and generation code, derive `childrenNames` as a comma-separated name string. This keeps `GuideRequest.children_names` compatible while making `children_ages` available for itinerary and content planning.

Alternative considered: encode ages in the existing name strings. That would be brittle, hard to validate, and hostile to downstream personalization.

### Decision 5: Pass child ages to itinerary discovery after they exist

The current flow runs attraction discovery before family details, so child ages are unavailable when suggestions are first loaded. The implementation should either:

- move family details before attractions, or
- allow attractions to load once with destination/preferences and refresh/re-rank after child ages are entered.

Use the least disruptive path: keep the requested step order with family details after attractions, but once ages are captured, use them for final guide content generation and for any later itinerary refresh. If product wants child ages to affect initial attraction suggestions, move family details before attractions in a follow-up decision.

This is the main trade-off in the requested order. The specs require ages to be available to itinerary discovery when discovery runs after age entry, but do not require blocking first attraction suggestions until family details are complete.

### Decision 6: Add a backend guide activity plan

Add explicit guide activity models to backend context, for example:

```python
class GuideActivity(BaseModel):
    destination_id: str
    type: Literal[
        "coloring",
        "word_search",
        "spot_the_difference",
        "detail_hunt",
        "drawing",
        "short_prompt",
        "checklist",
    ]
    title: str
    prompt: str
    complexity: Literal["preschool", "early_reader", "older_child", "family"]
    extension_prompt: str | None = None
```

`build_guide_context` should build a deterministic activity plan from selected destinations, selected landmarks, and child ages. `guide.html` should render destination activity pages from this plan.

Alternative considered: keep adding hard-coded pages directly in `guide.html`. That is faster for one activity but makes diversity and age complexity difficult to test.

### Decision 7: Use deterministic age bands and activity rotation

Use deterministic complexity bands:

- `preschool`: youngest child 3-5, or default for very young children.
- `early_reader`: youngest child 6-8.
- `older_child`: youngest child 9-12.
- `family`: fallback when ages are missing.

Use the youngest child as the baseline for mixed-age families and add optional extension prompts for older children. Rotate activity types across destinations/landmarks so guides with at least three activities use at least two types.

Alternative considered: AI-generate bespoke activity content per trip. That could be richer, but it introduces latency, cost, prompt risk, and weaker deterministic tests. Deterministic templates are more appropriate for this iteration.

## Risks / Trade-offs

- **Structured destinations still serialize to a text endpoint** -> The implementation should isolate serialization in a utility with unit tests so future API migration is local.
- **Child ages are collected after initial attraction suggestions** -> Ages will reliably influence final content; attraction suggestion re-ranking by age may require a refresh action unless the step order changes.
- **Changing `childrenList` shape can break existing components** -> Provide derived selectors/helpers for children names and ages, and update all consumers in one pass.
- **Six-step wizard affects existing flow tests** -> Update frontend tool tests to assert the new order rather than relying on the old five-step flow.
- **Activity diversity can expand template complexity** -> Keep activity rendering template-driven with a small set of activity types and focused CSS additions.
- **Name-only generation compatibility may conflict with age-aware content** -> Backend should default to `family` complexity when ages are omitted.

## Migration Plan

1. Add frontend helpers for destination and child records while keeping existing state names available through derived values.
2. Introduce the new destination and preferences components and update the wizard to six steps.
3. Update attraction discovery and review payload construction to use the new structured state.
4. Add backend child age parsing to `/api/generate` as optional form data.
5. Add guide activity models and activity planning in `build_guide_context`.
6. Render planned activities in `guide.html` and add CSS for new activity layouts.
7. Update and add frontend/backend tests.
8. Run Python tests, frontend node tests, lint/build where feasible.

Rollback strategy: revert the wizard to the previous five-step ordering and ignore optional `children_ages` in generation. Backend changes should remain backward-compatible because name-only guide generation continues to work.

## Open Questions

- Should child ages affect the initial attraction suggestion pass? If yes, family details must move before attractions, or attractions must refresh automatically after family details.
- What exact input format should "quando?" use in the UI: date picker, month/year, or short text? The first implementation can use a text field labeled "Quando?" to avoid overfitting before user research.
- Should activity pages be generated per destination or per selected landmark? The proposed implementation supports destination-level planning with landmark-aware prompts where available.
