## ADDED Requirements

### Requirement: Generated guide content order
The system SHALL generate guide content in a predictable order: welcome content, visual itinerary summary, destination content with activities, and final checklist or questions.

#### Scenario: Single destination guide
- **WHEN** the guide contains one destination
- **THEN** the generated guide includes welcome content
- **AND** it includes a visual itinerary summary
- **AND** it includes the single destination with at least two activities
- **AND** it ends with checklist or question content

#### Scenario: Multi-destination guide
- **WHEN** the guide contains multiple destinations
- **THEN** the generated guide includes welcome content
- **AND** it includes a visual itinerary summary
- **AND** it includes each destination in itinerary order with at least one activity per destination
- **AND** it ends with checklist or question content

### Requirement: Destination activity plan
The system SHALL build an explicit activity plan for the guide before rendering PDF/HTML content. The plan MUST associate each rendered activity with a destination, activity type, title, prompt, and age complexity level.

#### Scenario: Build activity plan for selected destinations
- **WHEN** guide context is built from selected destinations and landmarks
- **THEN** the guide context includes an activity plan for the selected destinations
- **AND** every activity in the plan references a destination included in the guide

#### Scenario: Render from activity plan
- **WHEN** PDF/HTML content is rendered
- **THEN** destination activities come from the guide activity plan
- **AND** the template does not rely only on hard-coded repeated activity pages

### Requirement: Activity type diversity
The system SHALL diversify activity types across the guide using family-friendly activity formats such as coloring, word search, spot-the-difference, detail hunt, drawing, short writing prompts, and checklist activities.

#### Scenario: Avoid one repeated activity type
- **WHEN** a guide has enough destination or landmark content for at least three activities
- **THEN** the generated activity plan uses at least two different activity types

#### Scenario: Include coloring as one activity option
- **WHEN** selected destination imagery or lineart is available
- **THEN** the activity planner can include a coloring activity using the available lineart image

#### Scenario: Include final checklist or questions
- **WHEN** the guide is generated
- **THEN** the guide ends with a checklist or question-based activity suitable for reflecting on the trip

### Requirement: Age-aware activity complexity
The system SHALL choose activity complexity from child ages and SHALL keep activity prompts understandable for the youngest child represented in the guide.

#### Scenario: Younger children receive simple activities
- **WHEN** the child age profile includes a child age 3 to 5
- **THEN** the generated activities favor simple formats such as coloring, drawing, observation, and checklist prompts

#### Scenario: Early readers receive moderate activities
- **WHEN** the child age profile includes children age 6 to 8 and no younger child
- **THEN** the generated activities can include short word search, simple question, checklist, and observation activities

#### Scenario: Older children receive harder activities
- **WHEN** the child age profile includes children age 9 to 12 and no younger child
- **THEN** the generated activities can include spot-the-difference, comparison, short writing, and challenge-style prompts

#### Scenario: Mixed-age families use the youngest child as baseline
- **WHEN** the guide includes children from multiple age bands
- **THEN** the generated activity complexity uses the youngest child's age band as the baseline
- **AND** activities can include optional extension prompts for older children

### Requirement: Guide generation accepts child age data
The backend guide generation path SHALL accept child age data without breaking existing guide generation for callers that only provide child names.

#### Scenario: Generate guide with child ages
- **WHEN** the frontend submits child names and ages for guide generation
- **THEN** the backend validates and stores the age data in the guide request context
- **AND** the generated guide uses the ages for activity complexity

#### Scenario: Preserve compatibility with name-only requests
- **WHEN** a request includes child names but omits child ages
- **THEN** the backend still generates a guide
- **AND** the activity planner uses a default family-friendly complexity

### Requirement: Renderable and testable guide output
The generated guide SHALL render as valid HTML for preview and PDF generation after activity planning is added.

#### Scenario: Preview renders planned sections
- **WHEN** the sample preview endpoint renders a guide
- **THEN** the HTML includes welcome, visual summary, destination activities, and final checklist or question sections

#### Scenario: PDF generation succeeds with planned activities
- **WHEN** a guide is generated with selected landmarks and child ages
- **THEN** the PDF generation path completes successfully
- **AND** the response includes a download URL
