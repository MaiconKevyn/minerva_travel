## ADDED Requirements

### Requirement: Destination-specific language content
The system SHALL add language learning content for destinations with a known relevant local language.

#### Scenario: Destination has known local language
- **WHEN** the guide includes a destination with known language metadata
- **THEN** the guide content plan includes language learning content for that destination
- **AND** the content includes phrase meaning and a child-friendly prompt

#### Scenario: Destination language is unknown
- **WHEN** the system cannot confidently determine a relevant language
- **THEN** it does not invent language tips
- **AND** guide generation still completes

### Requirement: Age-aware language complexity
The system SHALL adapt destination language tips and activities to the ages of the children in the guide.

#### Scenario: Younger children receive simple words
- **WHEN** the child age profile includes children age 3 to 5
- **THEN** language content uses simple words, matching, coloring, or observation prompts

#### Scenario: Older children receive phrase challenges
- **WHEN** the child age profile includes children age 9 to 12 and no younger child
- **THEN** language content can include short phrases, comparison prompts, or memory challenges

#### Scenario: Mixed-age family
- **WHEN** the guide includes children from multiple age bands
- **THEN** language content uses the youngest age band as the baseline
- **AND** it can include optional extension prompts for older children

### Requirement: Language content follows trip phases
The system SHALL place language learning content in pre-trip, during-trip, or post-trip guide moments when those phases are rendered.

#### Scenario: Pre-trip language moment
- **WHEN** the guide includes pre-trip content for a destination with known language metadata
- **THEN** the guide can introduce a small set of useful words or phrases before travel

#### Scenario: During-trip language moment
- **WHEN** the guide includes during-trip activities
- **THEN** language content can ask children to notice, say, or connect a phrase to a real place

#### Scenario: Post-trip language moment
- **WHEN** the guide includes post-trip reflection
- **THEN** language content can ask children to remember or reuse one learned word or phrase

### Requirement: Language content remains optional and bounded
The system SHALL keep destination language content optional and limited so it does not dominate the guide.

#### Scenario: Multiple destinations with languages
- **WHEN** a guide includes multiple destinations with known languages
- **THEN** the system limits language content per destination
- **AND** it keeps the main destination activity plan readable
