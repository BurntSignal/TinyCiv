# TinyCiv

TinyCiv runs autonomously. Open its web interface to observe the current civilization and chronicle.

One real hour equals one TinyCiv year. State is persistent across restarts and updates. The direct web port remains 8787, and Home Assistant Ingress is also supported.

The world-ending administrative control is intentionally destructive. Use it only when you mean to begin a new civilization.


## Observer notifications

When enabled, TinyCiv checks each civilization year for new Chronicle entries. A year with one or more entries produces exactly one spoiler-free alert: “A new chronicle entry has occurred!”

Home Assistant 2026.5+ Companion App devices can appear as notify entities. TinyCiv discovers those entities automatically. A single target is selected automatically; if multiple targets exist, choose one from the Observer Notifications card.
