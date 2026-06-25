## Context

The user can upload a cover photo during guide creation. When the uploaded photo contains multiple family members, the downstream illustration prompt or model output can collapse the group into a smaller subset. The product needs a deterministic contract around how family photos are described, validated, and handled when the generated cover is not good enough.

## Goals / Non-Goals

**Goals:**

- Preserve all visible people from a family cover photo in the generated illustration whenever technically possible.
- Track the expected family member count through the cover generation path.
- Fail gracefully by falling back to a safer cover treatment when validation is unavailable or fails.
- Keep guide generation working for existing requests that do not include family-photo metadata.

**Non-Goals:**

- Build a full face recognition or identity matching system.
- Store biometric identifiers or infer identities from the uploaded photo.
- Guarantee that an external image model will always produce a perfect count without fallback.

## Decisions

- Use expected person count as non-biometric metadata. The frontend can derive it from family records or ask for confirmation near the cover step; the backend treats it as a count, not as identity data.
- Strengthen prompt construction around group preservation. Prompts MUST explicitly request the same number of visible people, balanced composition, and no omitted family members.
- Add a validation abstraction instead of coupling implementation to one model vendor. The first implementation can be deterministic or metadata based, while future image analysis can be plugged in behind the same interface.
- Prefer a safe fallback over silently shipping a bad cover. If generated output cannot be trusted, the system can use the original uploaded photo treatment, regenerate once, or ask the user to confirm/replace the cover depending on product flow.

## Risks / Trade-offs

- External image generation may still omit people -> Mitigate with prompt constraints, one retry, and fallback.
- Person count validation can be imperfect -> Treat validation as a guardrail, not identity proof.
- Extra confirmation could slow the flow -> Only ask when expected count is unclear or validation fails.
- Storing extra metadata can raise privacy concerns -> Store only numeric count and transient generation context.
