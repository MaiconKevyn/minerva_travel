## ADDED Requirements

### Requirement: Destination learning page per selected destination

The system SHALL create exactly one `destination_intro` page for every selected destination that
contains at least one selected landmark, before that destination's first landmark page.

#### Scenario: Trip through several countries

- **WHEN** a guide selects landmarks in Paris and London
- **THEN** the ordered plan contains one Paris/France introduction before the Paris landmarks
- **AND** one London/England introduction before the London landmarks
- **AND** neither introduction is duplicated

### Requirement: Exact child-friendly destination copy

The system SHALL resolve bounded destination learning copy from server-trusted content and include
the exact title, country, learning points, label, and curiosity or observation in both the page
prompt and `required_copy`.

#### Scenario: Curated destination content exists

- **WHEN** the selected destination has editorial intro and curiosity content
- **THEN** the page renders two short learning points and one trusted curiosity
- **AND** regeneration keeps every string unchanged unless a new session is created

#### Scenario: Destination facts are unavailable

- **WHEN** no trusted curiosity is available
- **THEN** the page uses a non-factual `Missão de observação`
- **AND** the image model is told not to invent any fact

### Requirement: Destination pages contain no people

The system SHALL generate destination introductions without family or generic people.

#### Scenario: First generation and revision

- **WHEN** the first version is generated
- **THEN** no family reference is sent to the provider
- **WHEN** a selected version is revised
- **THEN** only that destination-page version is used as image input
- **AND** the people-free invariant overrides revision feedback

### Requirement: Landmark pages teach about the selected point

Every landmark page SHALL render a child-friendly description and either a trusted curiosity under
`Você sabia?` or a safe observation under `Missão de observação`.

#### Scenario: Landmark has no explicit curiosity field

- **WHEN** a landmark has a second trusted editorial description paragraph
- **THEN** the first paragraph is used as its description
- **AND** the second paragraph is presented as a trusted curiosity

#### Scenario: Unknown custom landmark

- **WHEN** no trusted landmark fact is available
- **THEN** the page uses a point-specific observation mission
- **AND** does not present the mission as a factual curiosity

### Requirement: Existing approval and PDF workflow remains generic

The system SHALL require destination pages to be generated and approved in sequence and SHALL
include their selected PNGs in the existing one-image-per-PDF-page export.

#### Scenario: Completed guide export

- **WHEN** every page including all destination introductions is approved
- **THEN** PDF export preserves the builder array order
- **AND** each approved destination PNG occupies one PDF page

### Requirement: Every landmark page has a printable visited checkbox

The system SHALL place one empty checkbox labeled exactly `Já visitei` in the footer of every
final `landmark` PNG, regardless of family inclusion or regeneration instruction.

#### Scenario: Landmark first generation and revision

- **WHEN** a landmark page is generated or regenerated
- **THEN** the model artwork reserves a calm footer area
- **AND** the server deterministically overlays one empty checkbox and `Já visitei`
- **AND** `Já visitei` appears in the page `required_copy`
- **AND** the approved PNG and final PDF preserve the checkbox
