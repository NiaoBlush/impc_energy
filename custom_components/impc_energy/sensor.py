"""GitHub sensor platform."""
import logging
import re
from datetime import timedelta
from typing import Any, Callable, Dict, Optional
from urllib import parse
import json

import aiohttp
# import gidgethub
import voluptuous as vol
# from aiohttp import ClientError

# from gidgethub.aiohttp import GitHubAPI

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_NAME,
    CONF_ACCESS_TOKEN,
    CONF_NAME,
    CONF_PATH,
    CONF_URL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from .energy_api import EnergyAPI

from .const import (
    # ATTR_CLONES,
    # ATTR_CLONES_UNIQUE,
    # ATTR_FORKS,
    # ATTR_LATEST_COMMIT_MESSAGE,
    # ATTR_LATEST_COMMIT_SHA,
    # ATTR_LATEST_OPEN_ISSUE_URL,
    # ATTR_LATEST_OPEN_PULL_REQUEST_URL,
    # ATTR_LATEST_RELEASE_TAG,
    # ATTR_LATEST_RELEASE_URL,
    # ATTR_OPEN_ISSUES,
    # ATTR_OPEN_PULL_REQUESTS,
    # ATTR_PATH,
    # ATTR_STARGAZERS,
    # ATTR_VIEWS,
    # ATTR_VIEWS_UNIQUE,
    BASE_API_URL
)

_LOGGER = logging.getLogger(__name__)
# Time between updating data from GitHub
SCAN_INTERVAL = timedelta(hours=1)

CONF_ACCOUNT_NUMBER = "account_number"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCOUNT_NUMBER): cv.string,
        vol.Required(ATTR_NAME): cv.string
    }
)


async def async_setup_platform(
        hass: HomeAssistantType,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    # github = GitHubAPI(session, "requester", oauth_token=config[CONF_ACCESS_TOKEN])
    # sensors = [GitHubRepoSensor(github, repo) for repo in config[CONF_REPOS]]
    energy_api = EnergyAPI(session, config[CONF_ACCOUNT_NUMBER])
    # addr = energy_api.get_basic()["name"]
    sensors = [ImpcBalanceSensor(energy_api, config[ATTR_NAME])]
    async_add_entities(sensors, update_before_add=True)


class ImpcBalanceSensor(Entity):
    def __init__(self, energy_api: EnergyAPI, name):
        super().__init__()

        self.energy_api = energy_api
        self._name = name
        self._state = None
        self._available = True
        self.attrs: Dict[str, Any] = {CONF_ACCOUNT_NUMBER: self.energy_api.account_number}

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.energy_api.account_number

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self):
        try:

            basic_data = await self.energy_api.get_basic()
            self.attrs["ttttattr"] = basic_data
            self._state = basic_data["balance"]
            self._available = True

        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving data from IMPC.")
