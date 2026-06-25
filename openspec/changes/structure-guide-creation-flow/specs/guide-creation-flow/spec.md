## ADDED Requirements

### Requirement: Structured destination entry
The system SHALL collect trip destinations as repeatable structured entries instead of a single primary freeform destination prompt. Each destination entry MUST include a place, travel timing, and number of days.

#### Scenario: Create a guide with one destination
- **WHEN** a user enters one destination with place, timing, and duration
- **THEN** the system stores that destination as a structured destination entry
- **AND** the user can continue to the next step

#### Scenario: Prevent incomplete destination submission
- **WHEN** a destination entry is missing place, timing, or duration
- **THEN** the system prevents the user from continuing
- **AND** the system identifies the missing destination field

#### Scenario: Create a guide with multiple destinations
- **WHEN** a user adds a second destination entry
- **THEN** the system stores both destinations in the order entered
- **AND** downstream itinerary discovery receives a serialized destination summary that preserves each place and duration

### Requirement: Destination list management
The system SHALL allow the user to add and remove destination entries while preserving at least one destination in the form.

#### Scenario: Add another destination
- **WHEN** the user selects "Adicionar destino"
- **THEN** the system appends a new empty destination entry after the existing entries

#### Scenario: Remove an extra destination
- **WHEN** the user removes a destination and more than one destination exists
- **THEN** the system removes only that destination
- **AND** the remaining destinations keep their relative order

#### Scenario: Preserve the required first destination
- **WHEN** only one destination exists
- **THEN** the system does not allow removing the last destination entry

### Requirement: Fixed trip preferences step
The system SHALL show trip preferences as a fixed step immediately after structured destinations and before attraction selection. Preferences MUST include trip pace and program categories that match the family.

#### Scenario: Preferences follow destinations
- **WHEN** the user completes structured destinations
- **THEN** the next step is the trip preferences step
- **AND** the attractions step is not shown until preferences are confirmed

#### Scenario: Select pace and programs
- **WHEN** the user selects a pace and one or more program categories
- **THEN** the system stores those preferences
- **AND** itinerary discovery uses the selected pace and categories

#### Scenario: Use default preferences
- **WHEN** the user does not customize preferences
- **THEN** the system uses a balanced pace and an empty category list as explicit defaults

### Requirement: Attraction suggestions complement known trip details
The system SHALL treat itinerary and attraction suggestions as a complement to user-provided trip details, not as a replacement for structured destination input.

#### Scenario: Suggested attractions use structured trip context
- **WHEN** the system requests attraction suggestions
- **THEN** the request includes the structured destinations, durations, pace, program categories, and child ages available at that point

#### Scenario: User can keep known places
- **WHEN** the system returns suggested attractions alongside places inferred from the destination context
- **THEN** the user can select which attractions enter the final guide
- **AND** the review step shows only selected attractions as confirmed guide content

### Requirement: Children include name and age
The system SHALL collect each child as a structured record with name and age. A guide MUST include at least one valid child record.

#### Scenario: Add child with age
- **WHEN** the user enters a child name and age
- **THEN** the system stores the child as a structured child record
- **AND** the age is available to itinerary and guide content generation

#### Scenario: Prevent child without age
- **WHEN** a child has a name but no valid age
- **THEN** the system prevents the user from continuing
- **AND** the system identifies the child age as required

#### Scenario: Send child ages to itinerary discovery
- **WHEN** itinerary discovery runs after children have been entered
- **THEN** the request includes `children_ages` derived from the child records

### Requirement: Six-step wizard order
The guide creation wizard SHALL guide the user through destinations, preferences, attractions, family details, cover photo, and review in that order.

#### Scenario: Wizard shows six steps
- **WHEN** the user starts guide creation
- **THEN** the system shows progress for six steps
- **AND** the steps are ordered as destinations, preferences, attractions, family details, cover photo, and review

#### Scenario: Review summarizes structured data
- **WHEN** the user reaches review
- **THEN** the review shows structured destinations, selected preferences, children with ages, responsible adults, cover photo status, and selected attractions

#### Scenario: Back navigation preserves data
- **WHEN** the user navigates backward from a later step
- **THEN** previously entered destinations, preferences, children, selected attractions, and cover photo remain available for editing
