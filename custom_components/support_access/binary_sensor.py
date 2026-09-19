"""Binary sensor platform for Support Access."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.auth import EVENT_USER_REMOVED, EVENT_USER_UPDATED
from homeassistant.auth.models import User
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import get_managed_user_ids
from .const import (
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
    """Set up Support Access binary sensor entities."""
    entities: list[LocalOnlyBinarySensor] = []
    for user_id in get_managed_user_ids(entry):
        user = await hass.auth.async_get_user(user_id)
        if user is None:
            _LOGGER.warning("Configured user %s no longer exists", user_id)
            continue
        entities.append(LocalOnlyBinarySensor(user))

    async_add_entities(entities)


class LocalOnlyBinarySensor(BinarySensorEntity):
    """Report whether a managed user is restricted to local login.

    On = local-only access is enabled (remote login blocked).
    Off = remote login is allowed.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:home-lock"
    _attr_device_class = BinarySensorDeviceClass.LOCK
    _attr_translation_key = "local_only_access"

    def __init__(self, user: User) -> None:
        """Initialize the binary sensor."""
        self._user = user
        self._user_id = user.id
        self._removed = False
        self._attr_unique_id = f"{DOMAIN}_{user.id}_local_only"
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
        """Return True when local-only access is enabled."""
        return not self._removed and self._user.local_only

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes describing the managed user."""
        return {
            ATTR_USER_ID: self._user_id,
            ATTR_USER_NAME: self._user.name,
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
