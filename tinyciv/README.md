# TinyCiv

A tiny autonomous self-hosted civilization.

## Release 0.5.8

TinyCiv can now send standards-based Web Push notifications directly to installed HTTPS PWAs. Notification subscriptions and the VAPID private key are stored in `TINYCIV_DATA_DIR`, outside the Git repository.

Open the installed TinyCiv PWA and tap **Enable notifications**. On iPhone/iPad, notification permission must be requested from the installed Home Screen web app. Use **Send test** to verify delivery immediately.

Only Chronicle events already marked by the simulation as noteworthy (`notify: true`) generate push alerts.

## Deployment

Current deployment: a systemd service in the Proxmox `webapps` LXC.

- Application code: `/opt/tinyciv`
- Persistent state: `/var/lib/tinyciv`
- Direct service port: `8787`

## Update

Import the release ZIP over the Git repository, commit and push, then update the running service with:

```bash
git -C /opt/tinyciv pull --ff-only
systemctl restart tinyciv
```

Persistent civilization state is stored outside the Git repository and is not replaced by application updates.
