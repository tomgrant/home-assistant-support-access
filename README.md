# Highlands Support Access

![Highlands Smart Homes](custom_components/support_access/brand/icon.png)

A [Highlands Smart Homes](https://highlandssmarthomes.com.au) Home Assistant integration that lets a homeowner temporarily grant **remote login** to selected users (for example a Highlands support technician), then lock them back to **local-network only**.

It uses Home Assistant's built-in per-user *“Can only log in from the local network”* (`local_only`) setting.

## What you get

For each managed user the integration creates:

| Entity | Meaning |
| --- | --- |
| `switch.*_remote_access` | **On** = user may log in remotely. **Off** = local network only. |
| `binary_sensor.*_local_only_access` | **On** = local-only restriction is active. |

Turning the switch **off** also revokes that user's active browser/app sessions, so an already-open remote session is ended.

## Requirements

- Home Assistant 2024.1 or newer
- [HACS](https://hacs.xyz/) (recommended install path)
- A dedicated support user already created under **Settings → People**

## Install with HACS

1. In HACS go to **Integrations** → menu (**⋮**) → **Custom repositories**
2. Add this repository URL as category **Integration**
3. Find **Highlands Support Access** in HACS and install it
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration** → **Highlands Support Access**
6. Select the user(s) to manage

### Manual install

Copy `custom_components/support_access` into your Home Assistant `config/custom_components/` folder, restart, then add the integration as above.

## Typical workflow

1. Create a user such as `highlands_support` (admin or limited, as you prefer).
2. Add that user in the Highlands Support Access config flow.
3. Leave **Remote access** off until help is needed.
4. When Highlands support needs remote access, turn the switch **on** (or automate it).
5. When finished, turn the switch **off**.

Example automation:

```yaml
alias: Enable Highlands support remote access for 2 hours
triggers:
  - trigger: event
    event_type: mobile_app_notification_action
    event_data:
      action: ENABLE_SUPPORT
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.highlands_support_remote_access
  - delay: "02:00:00"
  - action: switch.turn_off
    target:
      entity_id: switch.highlands_support_remote_access
```

## Notes

- This mirrors the same control as **Settings → People → user → “Can only log in from the local network”**.
- Behind some reverse proxies every client can appear “local”; in that case Home Assistant cannot distinguish remote logins. Prefer Nabu Casa / correctly configured proxy headers (`X-Forwarded-For` trusted).
- Long-lived access tokens for a local-only user are also rejected on remote requests.

## Changing managed users

**Settings → Devices & Services → Highlands Support Access → Configure**

## About Highlands Smart Homes

[highlandssmarthomes.com.au](https://highlandssmarthomes.com.au)

## License

MIT
