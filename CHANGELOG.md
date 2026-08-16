# TinyCiv 0.5.4

- Fixed the observer-belief Chronicle event so the root settlement name is inserted correctly instead of displaying the literal `{root}` placeholder.
- Added a one-time safe repair for any already-saved Chronicle entry containing that leaked placeholder.
- Audited the event text templates for other unexpanded named placeholders; no additional cases were found.
- No simulation balance or feature changes.
