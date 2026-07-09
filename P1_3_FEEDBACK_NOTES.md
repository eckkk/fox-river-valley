# P1.3 Playtest Feedback Notes

This update responds to the first external human-observed AI playtest feedback.

Observed needs:
- More readable house buildings and decorations so the home feels like it is growing.
- More workbench/tool crafting without creating duplicate item systems.
- Better public resource hints for AI blind play, especially for fiber, water, reeds, wood, and clay.
- Clearer water affordance through `look`, `inspect`, and `collect water`.
- Keep funny failure items such as `stinky_shoe` as rare fishing finds and possible joke decor.
- Make spoiled and near-expiry food easier to notice in `inventory`, `food`, and `status`.

Scope note:
- This patch is experience polish, not a rewrite.
- Internal `little_cabin` / `warm_cabin` logic remains compatible with existing relationship, commitment, and kit readiness checks.
- Player-facing house progression is presented as `simple_shelter -> cabin_frame -> small_cabin -> cozy_cabin`.
