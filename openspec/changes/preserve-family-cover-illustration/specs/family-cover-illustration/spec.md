## ADDED Requirements

### Requirement: Preserve visible family members in cover illustration
The system SHALL generate family cover illustrations that attempt to preserve every visible person represented by the uploaded family photo.

#### Scenario: Family photo has expected member count
- **WHEN** the user uploads a cover photo and the expected visible family member count is known
- **THEN** the cover generation request includes the expected count
- **AND** the image prompt requires the illustration to include the same number of visible family members

#### Scenario: Prompt avoids subset representation
- **WHEN** a family photo prompt is built for a group of people
- **THEN** the prompt explicitly rejects omitting, cropping out, or replacing family members with a smaller subset

### Requirement: Validate generated family cover count
The system SHALL validate generated family cover output against the expected visible family member count when validation is available.

#### Scenario: Generated output passes count validation
- **WHEN** validation detects at least the expected number of visible people in the generated cover
- **THEN** the generated cover can be used in preview and PDF generation

#### Scenario: Generated output fails count validation
- **WHEN** validation detects fewer visible people than expected
- **THEN** the system does not silently accept the generated cover
- **AND** it triggers the configured retry or fallback behavior

### Requirement: Safe fallback for uncertain cover generation
The system SHALL provide a safe fallback when family cover validation is unavailable, inconclusive, or failed after retry.

#### Scenario: Validation unavailable
- **WHEN** the system cannot validate the generated cover count
- **THEN** it uses a safer cover treatment or requests user confirmation before final generation

#### Scenario: Retry still fails
- **WHEN** a regenerated family cover still does not satisfy the expected count
- **THEN** the system falls back to the uploaded photo treatment or asks the user to replace the cover

### Requirement: Backward compatible cover generation
The system SHALL keep existing cover generation behavior working for requests that do not provide family-photo count metadata.

#### Scenario: Request has no expected count
- **WHEN** guide generation receives a cover photo without expected member count
- **THEN** guide generation still completes
- **AND** the system uses generic family-friendly cover generation behavior
