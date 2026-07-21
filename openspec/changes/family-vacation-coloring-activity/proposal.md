## Why

The current coloring activity depicts only a tourist landmark. Families also need a keepsake page
where children can color their own family on vacation while retaining the composition and visible
characteristics of the uploaded family photo.

## What Changes

- Add `family_coloring` as a fifth optional landmark-bound activity named
  `Família de férias para colorir`.
- Show a reviewed synthetic full-page example in the activity catalog and final builder panel.
- Use the private sanitized family photo as the primary identity/composition reference, plus an
  approved cover and landmark references when available.
- Generate original cozy rounded children's line art with bold contours, large closed regions and
  no shading, branding, named-artist imitation, or generated functional text.
- Apply the exact Portuguese title and instruction with the deterministic compositor.
- Keep the existing two-activities-per-landmark and eight-per-guide limits.

## Impact

- Optional activity type contracts and frontend catalog metadata.
- Progressive builder activity dispatch and family-photo dependency checks.
- Page-generation protocol, OpenAI reference assembly, prompt contracts and deterministic
  compositor.
- Backend, frontend, prompt, compositor and generation tests.

## Non-Goals

- Reproducing a named artist, commercial coloring-book brand, copyrighted character or page.
- Training or storing a reusable family model.
- Exposing the private family photo or its path in builder responses.
- Requiring the landmark page or cover to be approved before this activity can be generated.
