# Option 3 Plan: Systems Console

## Direction

Option 3 combines Option 1's living-terminal character with Option 2's structured professional dossier. The visual language is an intentionally dark systems console: precise typography, restrained cyan/green/amber signals, subtle motion, and a pseudo-3D delivery architecture.

## Profile structure

1. Generated pixel GitHub mark and animated terminal identity
2. Mission and operating principles
3. Capability command deck
4. Pseudo-3D delivery architecture showing Discover, Evaluate, Build, Validate, Adopt
5. Four selected-work case files
6. Experience, education, languages, status, and contact

## Design decisions

- Remove contribution calendars, activity counters, streaks, and repository statistics from the active README.
- Use no WebGL or JavaScript because GitHub README rendering does not support them.
- Simulate depth with SVG polygons, perspective grids, layered shadows, and moving signal packets.
- Keep all important content visible when animation is unavailable.
- Hide moving elements for visitors who request reduced motion.
- Use one dark visual treatment in both GitHub themes by design.
- Keep Option 1 and Option 2 untouched and switchable.

## Reliability

- All visual assets are generated locally from `config/profile.json`; the pixel GitHub mark is constructed directly from SVG dots and needs no source image.
- No third-party image, badge, font, analytics, or statistics service is required.
- The candidate is validated for local asset paths, alt text, SVG safety, animation fallback, and mobile file size.
