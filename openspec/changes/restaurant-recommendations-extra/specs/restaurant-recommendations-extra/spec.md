## ADDED Requirements

### Requirement: Optional paid restaurant add-on
The system SHALL offer restaurant recommendations as an explicit optional paid extra separate from the base guide.

#### Scenario: Extra is displayed
- **WHEN** the user reaches the add-on or checkout area
- **THEN** the restaurant recommendation extra is shown with its price
- **AND** the initial configured price is BRL 29.90

#### Scenario: Extra is not selected
- **WHEN** the user does not select or purchase the restaurant extra
- **THEN** guide generation does not include restaurant recommendations

### Requirement: Restaurant discovery near selected places
The system SHALL generate restaurant recommendations near selected map places, attractions, route areas, or destinations when the extra is enabled.

#### Scenario: Selected attractions are available
- **WHEN** the restaurant extra is enabled and selected attractions exist
- **THEN** restaurant discovery uses selected attractions as locality anchors
- **AND** each recommendation includes the nearby anchor context

#### Scenario: No selected attractions are available
- **WHEN** the restaurant extra is enabled but no selected attractions exist
- **THEN** restaurant discovery uses confirmed destinations as locality anchors

### Requirement: Family-friendly restaurant metadata
The system SHALL include practical family-friendly metadata for restaurant recommendations when available.

#### Scenario: Recommendation is shown
- **WHEN** a restaurant recommendation is rendered
- **THEN** it includes name, nearby context, short family-friendly reason, and any available notes such as cuisine or suitability

#### Scenario: Data is limited
- **WHEN** restaurant metadata is unavailable or uncertain
- **THEN** the system avoids inventing details
- **AND** it can render a shorter recommendation or omit that restaurant

### Requirement: Entitlement boundary for generated content
The system SHALL enforce that restaurant content is generated and rendered only when the restaurant extra is enabled for the guide.

#### Scenario: Backend request lacks entitlement
- **WHEN** a guide generation request does not include the restaurant extra entitlement
- **THEN** the backend omits restaurant discovery and restaurant sections

#### Scenario: Backend request includes entitlement
- **WHEN** a guide generation request includes the restaurant extra entitlement
- **THEN** the backend can generate and render restaurant recommendations in the optional section
