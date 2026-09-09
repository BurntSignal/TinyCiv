# TinyCiv 0.5.7

- Converted the active TinyCiv runtime into a standalone self-hosted web service.
- Removed the previous notification backend and notification-target discovery.
- Removed the Observer Notifications card from the web UI.
- Existing queued observer-notification jobs are acknowledged silently so future Web Push starts cleanly with new Chronicle events.
- Replaced old host-specific branding in the web UI, PWA manifest, and documentation.
- Added Python cache exclusions so generated `__pycache__` / `.pyc` files no longer interfere with Git updates.
- Civilization simulation behavior remains unchanged from 0.5.6; existing worlds and Chronicle history are preserved.
- PWA Web Push is planned after HTTPS is configured.

# TinyCiv 0.5.6

- Broke Tinkerfen out of the centuries-long Machine Age plateau with a concrete technology chain extending through electrification, telegraphy, engines, industrial chemistry, radio, flight, antibiotics, electronics, digital computing, orbital rocketry, networking, satellites, grid storage, and reusable orbital launch.
- Added Industrial, Modern, Electronic, Information, and Space Ages. Later eras now require actual capabilities rather than an abstract knowledge score.
- Reworked discoveries into a prerequisite chain so a high-knowledge old civilization advances through real inventions instead of skipping straight to futuristic technology.
- Added persistent development threads: discoveries now create later Chronicle consequences such as electrification, motorization, mass media, computing, network society, and infrastructure/regulatory responses.
- Revived the Watcher belief as a persistent cultural thread capable of developing congregations, schism, and later conflict with scientific thought.
- Chronicle selection is stricter in mature civilizations. Exhausted exploration no longer emits generic map-filling filler, and festivals/economic/cultural categories have stronger cooldowns.
- Discovery and development events receive much higher priority once old progression has been exhausted.
- Generic prosperity wording was replaced with a more concrete historical consequence.
- Existing worlds migrate in place. Tinkerfen's history, population, contacts, settlements, and Chronicle are preserved.
