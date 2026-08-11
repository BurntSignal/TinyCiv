# TinyCiv 0.3.2

- Added spoiler-free Chronicle push notifications through Home Assistant.
- Once per civilization year, if one or more new Chronicle entries occur, TinyCiv sends one alert: “A new chronicle entry has occurred!”
- Notification text never reveals the year, event count, or what happened.
- Added an Observer Notifications card that discovers Home Assistant notify entities, auto-selects a single available target, allows choosing among multiple targets, and provides a test button.
- Notification delivery is now queued persistently, preventing events from being missed if the PWA advances the simulation before the background worker.
- If push delivery is unavailable, TinyCiv falls back to a spoiler-free Home Assistant persistent notification.
- Existing civilizations and Chronicle history persist; no world reset required.
