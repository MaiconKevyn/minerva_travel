## ADDED Requirements

### Requirement: Broader attraction category coverage
The system SHALL request and return attraction options across a broader set of family-friendly categories when source data is available.

#### Scenario: Destination has multiple attraction categories
- **WHEN** attraction discovery runs for a destination with available place data
- **THEN** returned options include more than one category
- **AND** categories can include parks, squares, theaters, museums or art, outdoor programs, local stores, and family activities

#### Scenario: Family preferences are available
- **WHEN** trip pace, program categories, and child ages are available
- **THEN** attraction discovery uses those inputs to prioritize relevant options within the broader category set

### Requirement: Minimum useful option set
The system SHALL aim to provide enough attraction options per destination for meaningful user choice.

#### Scenario: Destination has sufficient source data
- **WHEN** a destination has enough candidate places
- **THEN** the system presents a minimum useful set of categorized options for that destination

#### Scenario: Destination has limited source data
- **WHEN** fewer candidate places are available than the target option count
- **THEN** the system presents the available options without duplicating or inventing places

### Requirement: Categorized attraction selection
The system SHALL make attraction categories visible during selection and preserve only user-selected attractions for guide generation.

#### Scenario: User reviews categorized options
- **WHEN** attraction options are shown
- **THEN** each option includes a category label or grouping
- **AND** the user can select or deselect individual places

#### Scenario: Guide generation uses selected options
- **WHEN** the user generates the guide
- **THEN** only selected attraction options are sent as confirmed guide content

### Requirement: Attraction diversity is testable
The system SHALL expose enough normalized attraction metadata to test diversity and selected-place preservation.

#### Scenario: Discovery response is normalized
- **WHEN** attraction discovery returns options
- **THEN** each normalized option includes destination, title, category, and selection identity
