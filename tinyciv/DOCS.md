# TinyCiv

TinyCiv runs autonomously. Open its web interface to observe the current civilization and Chronicle.

One real hour equals one TinyCiv year. State is persistent across restarts and application updates.

## Hosting

TinyCiv is a standalone self-hosted web service. The application listens on port `8787` by default and stores persistent civilization state in the directory configured by `TINYCIV_DATA_DIR`.

## Observer notifications

The previous observer-notification integration was removed in 0.5.7 as part of the standalone migration.

Push notifications are intentionally disabled for now. A future HTTPS release will use PWA Web Push directly.

## Destructive control

The world-ending administrative control is intentionally destructive. Use it only when you mean to begin a new civilization.
