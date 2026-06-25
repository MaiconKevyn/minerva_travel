## ADDED Requirements

### Requirement: Itinerary mode selection
The system SHALL let users choose whether they already know the itinerary or want AI help suggesting one.

#### Scenario: User chooses known itinerary
- **WHEN** the user selects the known-itinerary mode
- **THEN** the system shows structured destination entry as the primary path
- **AND** the user can add destinations with place, timing, duration, and order

#### Scenario: User chooses AI suggestion mode
- **WHEN** the user selects the AI-suggested itinerary mode
- **THEN** the system asks for enough trip constraints to suggest route options
- **AND** it does not proceed to attraction selection until the user confirms structured destinations

### Requirement: Freeform itinerary follow-up
The system SHALL convert freeform itinerary text into structured destinations and ask targeted follow-up questions for missing fields.

#### Scenario: Freeform text omits destination duration
- **WHEN** the user enters freeform route text with destinations but missing duration
- **THEN** the system asks how many days the family will stay in each affected destination

#### Scenario: Freeform text omits itinerary order
- **WHEN** the user enters multiple destinations without a clear order
- **THEN** the system asks the user to confirm or reorder the destinations before continuing

### Requirement: Suggested itinerary options become editable destinations
The system SHALL present AI-suggested itinerary options as editable structured destination records before attraction discovery.

#### Scenario: User accepts suggested route
- **WHEN** the user accepts an AI-suggested route
- **THEN** the selected route becomes the structured destination list
- **AND** the user can edit destination place, timing, duration, and order

#### Scenario: User rejects suggested route
- **WHEN** the user rejects all suggested route options
- **THEN** the system keeps the user in itinerary input mode
- **AND** the user can enter destinations manually

### Requirement: Downstream compatibility
The system SHALL send the same structured destination contract to attraction discovery and guide generation regardless of itinerary input mode.

#### Scenario: Attractions requested after freeform conversion
- **WHEN** converted freeform destinations are confirmed
- **THEN** attraction discovery receives structured destinations with place, timing, duration, and order

#### Scenario: Guide generated after AI route acceptance
- **WHEN** a guide is generated from an accepted AI-suggested route
- **THEN** guide generation receives the confirmed structured destinations, not the raw suggestion text only
