"""Switch platform for Support Access."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.auth import EVENT_USER_REMOVED, EVENT_USER_UPDATED
from homeassistant.auth.models import TOKEN_TYPE_NORMAL, User
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import get_managed_user_ids
from .const import (
    ATTR_LOCAL_ONLY,
    ATTR_USER_ID,
    ATTR_USER_NAME,
    BRAND_URL,
    DOMAIN,
    MANUFACTURER,
    MODEL_SUPPORT_USER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Support Access switch entities."""
    entities: list[RemoteAccessSwitch] = []
    for user_id in get_managed_user_ids(entry):
        user = await hass.auth.async_get_user(user_id)
        if user is None:
            _LOGGER.warning("Configured user %s no longer exists", user_id)
            continue
        entities.append(RemoteAccessSwitch(user))

    async_add_entities(entities)


class RemoteAccessSwitch(SwitchEntity):
    """Toggle remote login for a managed Home Assistant user.

    On = remote login allowed (``local_only=False``).
    Off = local-network login only (``local_only=True``).
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:remote-desktop"
    _attr_translation_key = "remote_access"

    def __init__(self, user: User) -> None:
        """Initialize the switch."""
        self._user = user
        self._user_id = user.id
        self._removed = False
        self._attr_unique_id = f"{DOMAIN}_{user.id}_remote_access"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, user.id)},
            name=user.name or f"User {user.id[:8]}",
            manufacturer=MANUFACTURER,
            model=MODEL_SUPPORT_USER,
            configuration_url=BRAND_URL,
        )

    @property
    def available(self) -> bool:
        """Return True while the managed user still exists."""
        return not self._removed

    @property
    def is_on(self) -> bool:
        """Return True when remote login is allowed."""
        return not self._removed and not self._user.local_only

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes describing the managed user."""
        return {
            ATTR_USER_ID: self._user_id,
            ATTR_USER_NAME: self._user.name,
            ATTR_LOCAL_ONLY: self._user.local_only,
        }

    async def async_added_to_hass(self) -> None:
        """Register listeners when the entity is added."""
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_USER_UPDATED, self._handle_user_event)
        )
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_USER_REMOVED, self._handle_user_removed)
        )

    @callback
    def _handle_user_event(self, event: Event) -> None:
        """Refresh state when the managed user changes."""
        if event.data.get("user_id") != self._user_id:
            return
        self.async_write_ha_state()

    @callback
    def _handle_user_removed(self, event: Event) -> None:
        """Mark unavailable when the managed user is deleted."""
        if event.data.get("user_id") != self._user_id:
            return
        self._removed = True
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allow the user to log in remotely."""
        if self._removed:
            _LOGGER.error("Cannot enable remote access; user %s missing", self._user_id)
            return

        await self.hass.auth.async_update_user(self._user, local_only=False)
        self.async_write_ha_state()
        _LOGGER.info(
            "Remote access enabled for user %s", self._user.name or self._user.id
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Restrict the user to local-network login only."""
        if self._removed:
            _LOGGER.error(
                "Cannot disable remote access; user %s missing", self._user_id
            )
            return

        await self.hass.auth.async_update_user(self._user, local_only=True)

        # End active browser/app sessions so remote clients must re-authenticate
        # (and will then be blocked while local_only is set).
        for token in list(self._user.refresh_tokens.values()):
            if token.token_type == TOKEN_TYPE_NORMAL:
                self.hass.auth.async_remove_refresh_token(token)

        self.async_write_ha_state()
        _LOGGER.info(
            "Remote access disabled for user %s", self._user.name or self._user.id
        )
