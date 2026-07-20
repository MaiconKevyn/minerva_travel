## Why

Families currently discover visual mistakes only after the complete HTML/PDF pipeline finishes. The product needs a page-first workflow where every generated guide page is visible in the browser as soon as it is ready, can be regenerated, and must be explicitly approved before the family moves to the next page.

The first experiment must also validate the current OpenAI image model's ability to render real guide copy inside the artwork. The cover should combine the uploaded family photo, an illustrated treatment, the exact family name, and the trip date. The second page should be a complete illustrated summary containing the exact confirmed destination and landmark names.

## What Changes

- Replace the current automatic block generation experience with an ordered page-generation workflow.
- Generate a complete vertical PNG for each page, including its required visible text, using the OpenAI Image API.
- Start with the cover and illustrated trip summary, while representing subsequent guide pages through the same ordered page contract.
- Require an explicit user action to generate, approve, or regenerate each page.
- Let the user describe what should change in a regeneration, using the selected attempt as a
  visual reference; when the field is empty, request a visibly different alternative instead of
  repeating the same composition.
- Display generated page images directly in the authenticated UI without waiting for a PDF, then
  let the family explicitly export the approved sequence as a downloadable PDF.
- Treat provider failures as visible retryable errors; never substitute a placeholder, raw family photo, or legacy PDF generation.
- Preserve the exact approved image attempt so later export can reuse the same pixels.
- Assemble the approved PNGs in page order into a full-bleed PDF with one image per page, without
  rerunning image generation or the legacy HTML guide renderer.
- Treat the approved cover and original family photo as canonical identity references for the
  summary and for destination pages where the family is explicitly included, preventing the
  model from inventing a different family.
- Generate destination/landmark pages without people by default and expose an opt-in
  `Incluir família` control for each attempt.
- Apply owner isolation, attempt limits, request quotas, idempotency, retention, and account-deletion behavior to page-generation sessions and assets.

## Capabilities

### New Capabilities

- `progressive-guide-page-generation`: Ordered full-page image generation, page attempts,
  approval, regeneration, progressive UI review, and approved-image PDF export.
- `openai-guide-page-art`: OpenAI image editing/generation for family cover, itinerary summary,
  and optional-family destination pages with exact in-image copy.

### Modified Capabilities

- `guide-content-generation`: The browser-visible guide is assembled from approved page images;
  its final PDF is a deterministic packaging of those exact images.
- `preserve-family-cover-illustration`: Cover identity guardrails apply to the complete generated cover page rather than an illustration later wrapped by HTML.

## Impact

- Backend page-session models and persistence.
- OpenAI image provider configuration and prompts.
- Authenticated asset-serving and page-attempt endpoints.
- Final review step and progressive page UI.
- Request-control, retention, privacy deletion, and observability paths.
- Backend, frontend, integration, and live visual smoke tests.

## Non-Goals

- Reintroducing the legacy HTML-to-PDF guide layout or regenerating content during PDF export.
- Automatically accepting a generated page without user review.
- Silently falling back to placeholders, the original photo, or the legacy one-click generator.
- Guaranteeing perfect typography from every model attempt; the product exposes regeneration and explicit approval so the experiment can measure real output quality.
