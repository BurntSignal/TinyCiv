# TinyCiv

A tiny autonomous civilization that lives on a Home Assistant server.

## V1 rules

- 1 real hour = 1 TinyCiv year.
- The civilization runs autonomously. You observe; you do not steer.
- State persists across Home Assistant restarts.
- If TinyCiv is offline, it catches up based on elapsed real time when it starts again.
- The dashboard includes a "Since your last visit..." report.
- Important events and 25-year milestones can create Home Assistant persistent notifications.
- The only direct intervention is **Nuke civilization**, which creates an entirely new world.

## Install in Home Assistant

1. Put this repository on GitHub.
2. In Home Assistant, open **Settings → Apps → App store**.
3. Open the repository manager and add this repository's GitHub URL.
4. Refresh/check for updates.
5. Install **TinyCiv**.
6. Start it and open the Web UI, or browse to `http://homeassistant.local:8787`.

## Development

Every time `config.yaml` changes for a new release, bump the `version` number so Home Assistant sees the update.

TinyCiv's persistent state is stored inside the app's `/data` volume as `tinyciv_state.json`.
