# Data Registry Guide

This guide is for future maintainers adding small data entries without turning Fox River Valley into a bigger system.

## flower variety

Add flower varieties in the flower registry/table only. Each variety should have a stable item id, display flavor, color text, preferred seasons, and any rare-yield hook. Keep `flower_seed` deterministic by seed and plot context.

## companion profile

Add a `companion profile` when a play style needs preferences. A profile can set preferred commitment tokens, favorite flower, family species, or hidden breed. Silas/Yaya profile 是示例, not a global rule.

## commitment token

Add a `commitment token` by tagging an item as `commitment_token`. The default profile should accept any valid token. Profile-specific preferences should be optional bonuses, not hard global gates.

## family species

Add a `family species` in the family species registry with a display name, hidden breed display if needed, a small trait list, and a favorite place. Keep species fictional and self-contained.

## hidden material

Add a `hidden material` through exploration or ruins/fishing findings. Include a short source hint and future-use hint in `materials log`, but do not unlock large systems by accident.

## recipe

Add a `recipe` in the recipe/build table with clear inputs, output count, and station requirement if any. Basic hand recipes should stay simple; advanced tools or furniture should declare workbench, campfire, kiln, loom, or hearth needs.

## exploration event

Add an `exploration event` as a deterministic, seed-stable rule keyed by terrain, nearby terrain, weather, season, or time. Keep event text short and avoid long quest chains.

## Profile Boundary

foxbell / silicon_fox are Silas/Yaya profile preferences. They are allowed as a warm example path, but they must not become the only route for all players. New default-profile players should still be able to choose different commitment tokens and species where the rules allow it.
