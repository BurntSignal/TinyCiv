# TinyCiv

A tiny autonomous civilization living inside Home Assistant.

## Release 0.5.3

Knowledge is no longer presented or simulated as a percentage with an artificial ceiling. It is now an unbounded civilization index, so a society can continue accumulating knowledge beyond 100 instead of eventually reaching a misleading state of “100% knowledge.”

The Knowledge card keeps its since-last-visit delta, but now displays a plain number. Food, Health, Morale, and Stability remain 0–100 condition metrics.

The observer remains exactly that: an observer. This update adds no controls, choices, tech tree, or direct influence over the civilization.

## Install / update

Import this release over the existing repository, commit and push, then use Home Assistant Apps to check for updates and update TinyCiv. Existing `/data` state and Chronicle history are preserved.

No Home Assistant automation or YAML changes are required. If an existing civilization has already reached Knowledge 100, it can resume accumulating knowledge naturally after the update.
