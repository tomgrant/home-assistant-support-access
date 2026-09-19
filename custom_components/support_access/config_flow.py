"""Config flow for Support Access."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import CONF_USER_IDS, DOMAIN


async def _user_options(hass: HomeAssistant) -> list[dict[str, str]]:
    """Build selectable options for non-system Home Assistant users."""
    options: list[dict[str, str]] = []
    for user in await hass.auth.async_get_users():
        if user.system_generated or not user.is_active:
            continue
        label = user.name or user.id
        if user.is_owner:
            label = f"{label} (owner)"
        options.append({"value": user.id, "label": label})
    return sorted(options, key=lambda item: item["label"].lower())


async def _users_schema(
    hass: HomeAssistant, defaults: list[str] | None = None
) -> vol.Schema:
    """Return the multi-select schema for choosing users."""
    options = await _user_options(hass)
    return vol.Schema(
        {
            vol.Required(CONF_USER_IDS, default=defaults or []): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


class SupportAccessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Support Access."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            user_ids = user_input.get(CONF_USER_IDS, [])
            if not user_ids:
                errors["base"] = "no_users"
            else:
                names: list[str] = []
                for user_id in user_ids:
                    user = await self.hass.auth.async_get_user(user_id)
                    if user is None:
                        errors["base"] = "invalid_user"
                        break
                    names.append(user.name or user_id)
                if not errors:
                    title = "Support Access"
                    if len(names) == 1:
                        title = f"Support Access ({names[0]})"
                    return self.async_create_entry(
                        title=title,
                        data={CONF_USER_IDS: user_ids},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=await _users_schema(self.hass),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SupportAccessOptionsFlow()


class SupportAccessOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Support Access."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        current = list(
            self.config_entry.options.get(
                CONF_USER_IDS, self.config_entry.data.get(CONF_USER_IDS, [])
            )
        )

        if user_input is not None:
            user_ids = user_input.get(CONF_USER_IDS, [])
            if not user_ids:
                errors["base"] = "no_users"
            else:
                return self.async_create_entry(title="", data={CONF_USER_IDS: user_ids})

        return self.async_show_form(
            step_id="init",
            data_schema=await _users_schema(self.hass, defaults=current),
            errors=errors,
        )
