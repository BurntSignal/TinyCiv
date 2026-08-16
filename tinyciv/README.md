# TinyCiv

A tiny autonomous civilization living inside Home Assistant.

## Release 0.5.4

Tiny Chronicle hotfix: the observer-belief entry now resolves the civilization's root settlement name correctly instead of ever exposing the internal `{root}` placeholder.

Existing Chronicle history is preserved. If that literal placeholder was already written into a civilization's Chronicle, TinyCiv repairs the saved entry automatically when the updated state is loaded.

No simulation balance, event frequency, observer controls, or other behavior has changed.

## Install / update

Import this release over the existing repository, commit and push, then use Home Assistant Apps to check for updates and update TinyCiv. Existing `/data` state and Chronicle history are preserved.

No Home Assistant automation or YAML changes are required.
