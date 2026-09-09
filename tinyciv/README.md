# TinyCiv

A tiny autonomous self-hosted civilization.

## Release 0.5.7

TinyCiv now runs as a standalone web service. The old observer-notification backend and notification UI have been removed. Chronicle push notifications will return later using native PWA Web Push once HTTPS is configured.

The civilization simulation itself is unchanged from 0.5.6. Existing state and Chronicle history remain in the external data directory configured by `TINYCIV_DATA_DIR`.

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
