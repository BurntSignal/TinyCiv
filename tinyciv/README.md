# TinyCiv

A tiny autonomous civilization living inside Home Assistant.

## Release 0.3.2

TinyCiv can now send spoiler-free Chronicle alerts through Home Assistant. If a civilization year produces any Chronicle entry, one generic notification is sent without revealing what happened.

## Install / update

Import this release over the existing repository, commit and push, then use Home Assistant Apps to check for updates and update TinyCiv. Existing `/data` state is preserved.

After updating, open TinyCiv and check **Observer Notifications**. If Home Assistant exposes only one notify entity, TinyCiv selects it automatically. If there are several, choose your phone and use **Send test notification**. No Home Assistant automation or YAML is required.
