## 1. Language Metadata And Tests

- [x] 1.1 Add tests for destination language lookup with known and unknown destinations.
- [x] 1.2 Add guide builder tests for language content with child age bands 3-5, 6-8, 9-12, mixed ages, and missing ages.
- [x] 1.3 Add render tests proving language content appears in the expected guide phase when available.

## 2. Content Planning

- [x] 2.1 Add destination language metadata utilities or a curated language mapping.
- [x] 2.2 Add structured language activity records to the guide content plan.
- [x] 2.3 Generate age-aware phrase prompts using the existing activity complexity rules.
- [x] 2.4 Limit language content per destination and omit it when language metadata is uncertain.

## 3. Rendering And API Compatibility

- [x] 3.1 Render language learning moments inside pre-trip, during-trip, or post-trip sections.
- [x] 3.2 Ensure PDF generation still works when no language content is available.
- [x] 3.3 Preserve existing guide generation request contracts without requiring new user input.

## 4. Verification

- [x] 4.1 Run backend guide builder and render tests.
- [x] 4.2 Run frontend or integration tests affected by guide preview/PDF content.
- [x] 4.3 Run `openspec validate destination-language-learning --strict`.
