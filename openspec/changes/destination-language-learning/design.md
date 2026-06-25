## Context

The guide already has destination activities and can use child ages for complexity. Feedback adds a specific content type: language tips and learning moments based on the destination. This should fit the guide content structure rather than becoming an unrelated appendix.

## Goals / Non-Goals

**Goals:**

- Add useful destination-language phrases and mini activities.
- Adapt complexity to child ages.
- Support pre-trip interest, during-trip observation/reinforcement, and post-trip memory prompts.
- Avoid misleading language content when destination language is unknown.

**Non-Goals:**

- Provide full language lessons or translation services.
- Support every dialect or regional language nuance in the first implementation.
- Require users to answer additional language questions during guide creation.

## Decisions

- Use destination metadata to infer language. A small curated mapping can cover common destinations first, with fallback to no language section when unknown.
- Generate language items as structured guide activities. Each item should include phrase, pronunciation helper when available, meaning, prompt, destination, and age band.
- Place language content in existing guide phases. Pre-trip can introduce phrases, during-trip can ask children to spot/use words, and post-trip can reinforce memories.
- Use child age bands from the existing guide activity planner. Younger children get simple words and matching; older children can get phrase challenges or short writing prompts.

## Risks / Trade-offs

- Incorrect language inference can reduce trust -> Prefer omission or generic cultural note when uncertain.
- Pronunciation can be hard to represent -> Keep pronunciation helpers simple and optional.
- Extra content can bloat the guide -> Limit language items per destination and reuse phase structure.
