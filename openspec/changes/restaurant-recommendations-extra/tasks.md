## 1. Pricing And Entitlement Contract

- [x] 1.1 Add tests for restaurant extra selection, price display, and guide-generation entitlement payloads.
- [x] 1.2 Add backend tests proving restaurant content is omitted without the entitlement.
- [x] 1.3 Add backend tests proving restaurant discovery runs when entitlement is present.

## 2. Restaurant Discovery

- [x] 2.1 Add product configuration for the restaurant extra price with initial value BRL 29.90.
- [x] 2.2 Add restaurant extra state to the frontend flow or checkout handoff.
- [x] 2.3 Implement restaurant discovery anchored to selected attractions or confirmed destinations.
- [x] 2.4 Normalize restaurant recommendations with name, nearby context, reason, cuisine or suitability notes when available.

## 3. Guide Rendering

- [x] 3.1 Render restaurant recommendations in a separate optional guide section when the extra is enabled.
- [x] 3.2 Ensure the base guide layout is unchanged when the extra is not enabled.
- [x] 3.3 Add a freshness note that recommendations should be checked before visiting.

## 4. Verification

- [x] 4.1 Run frontend tests for add-on display and payload state.
- [x] 4.2 Run backend tests for entitlement, discovery, and rendering.
- [x] 4.3 Run `openspec validate restaurant-recommendations-extra --strict`.
