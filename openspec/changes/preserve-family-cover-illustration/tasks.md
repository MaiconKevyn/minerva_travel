## 1. Cover Metadata And Tests

- [x] 1.1 Add tests for preserving expected family member count through cover upload, review, and generation payloads.
- [x] 1.2 Add backend tests for cover prompt generation with expected counts of two, three, and four or more people.
- [x] 1.3 Add a regression test proving guide generation still works when expected cover member count is omitted.

## 2. Prompt And Validation Implementation

- [x] 2.1 Extend cover generation payloads to include optional expected visible family member count.
- [x] 2.2 Update cover prompt construction to require the same number of visible family members as the uploaded photo.
- [x] 2.3 Add a validation interface for generated cover outputs that can compare detected count with expected count.
- [x] 2.4 Implement retry or fallback behavior when validation fails or is inconclusive.

## 3. Frontend Flow

- [x] 3.1 Capture or derive expected family member count in the cover photo step without requiring identity recognition.
- [x] 3.2 Show a recoverable state when cover generation cannot confidently preserve the full family group.
- [x] 3.3 Ensure the review step keeps the selected cover fallback or confirmed generated cover.

## 4. Verification

- [x] 4.1 Run backend tests covering prompt generation, fallback, and guide generation.
- [x] 4.2 Run frontend tests covering cover metadata serialization and review state.
- [x] 4.3 Run `openspec validate preserve-family-cover-illustration --strict`.
