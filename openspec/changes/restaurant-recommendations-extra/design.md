## Context

Restaurant recommendations were suggested as an extra paid feature. The feature depends on selected destinations or map places and should not be included in the base guide unless the user explicitly opts in.

## Goals / Non-Goals

**Goals:**

- Offer a clearly priced restaurant recommendation add-on.
- Generate restaurant tips near selected attractions, route areas, or destinations.
- Keep recommendations family-friendly and practical.
- Prevent unpaid add-on content from appearing in generated guides.

**Non-Goals:**

- Build a full checkout system if one does not already exist.
- Guarantee reservations, live availability, or current menu prices.
- Replace external restaurant platforms.

## Decisions

- Model restaurants as an optional guide extra. The request should include an explicit add-on flag or entitlement before restaurant content is generated.
- Price is product configuration. Use BRL 29.90 as the initial display/contract value, but keep it centralized for future pricing changes.
- Anchor recommendations to selected places. Each restaurant suggestion should include the nearby attraction/destination context and a family-friendly reason.
- Keep base guide generation isolated. If the add-on is not selected or entitlement is missing, the backend omits restaurant discovery and rendering.

## Risks / Trade-offs

- Restaurant data can become stale -> Include a freshness disclaimer and avoid promising availability.
- Monetization flow may not be ready -> Implement entitlement boundaries so UI and payment can be integrated incrementally.
- Extra content can clutter the guide -> Render restaurants in a separate optional section near itinerary context.
