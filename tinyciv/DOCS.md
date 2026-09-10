# TinyCiv

TinyCiv runs autonomously. Open its web interface to observe the current civilization and Chronicle.

One real hour equals one TinyCiv year. State is persistent across restarts and application updates.

## Hosting

TinyCiv is a standalone self-hosted web service. The application listens on port `8787` by default and stores persistent civilization state in the directory configured by `TINYCIV_DATA_DIR`.

## Web Push notifications

TinyCiv can deliver Chronicle alerts directly through standards-based Web Push.

Requirements:
- serve TinyCiv over trusted HTTPS;
- install/open TinyCiv as a Home Screen PWA on iPhone/iPad;
- tap **Enable notifications** inside the PWA and allow the system permission prompt.

Push subscriptions are stored in `push_subscriptions.json` and the generated VAPID private key in `vapid_private_key.pem`, both under `TINYCIV_DATA_DIR`.

Use **Send test** after subscribing to verify the complete push path.

## Destructive control

The world-ending administrative control is intentionally destructive. Use it only when you mean to begin a new civilization.
