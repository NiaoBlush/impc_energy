"""GitHub sensor platform."""
import datetime
import logging
import random
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

tz = datetime.timezone(timedelta(hours=+8))

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
    DOMAIN,
    ATTR_BALANCE,
    ATTR_ACCOUNT_NUMBER
)

_LOGGER = logging.getLogger(__name__)

# Time between updating data
SCAN_INTERVAL = timedelta(hours=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_ACCOUNT_NUMBER): cv.string,
        vol.Optional(ATTR_NAME): cv.string
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
    energy_api = EnergyAPI(session, config[ATTR_ACCOUNT_NUMBER])

    basic_info = await energy_api.get_basic()
    account_name = basic_info[ATTR_NAME]
    energy_api.set_account_name(account_name)
    name_in_entity = config[ATTR_NAME] if config.__contains__(ATTR_NAME) else account_name

    sensors = []
    sensors.append(ImpcBalanceSensor(energy_api, name_in_entity))
    # sensors.append(MyMonthlyChartSensor())

    async_add_entities(sensors, update_before_add=True)


class ImpcBalanceSensor(Entity):
    def __init__(self, energy_api: EnergyAPI, name):
        super().__init__()

        self._energy_api = energy_api
        self._name = f"{name}_电费余额"
        self._state = None
        self._available = False
        self._data = None
        self._attrs: Dict[str, Any] = {
            "户名": energy_api.account_name,
            "户号": energy_api.account_number,
            "说明": "查询余额为结算系统余额=上月度结转电费+本月缴纳电费。实际电费余额以表计显示为准"
        }

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def entity_id(self) -> str:
        return f"sensor.{DOMAIN}_{self._energy_api.account_number}_{ATTR_BALANCE}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def data(self) -> Optional[float]:
        return self._data

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return '元'

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    async def async_update(self):
        try:

            basic_data = await self._energy_api.get_basic()
            self._state = self._data = basic_data[ATTR_BALANCE]
            self._attrs["last_query"] = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            self._available = True

        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving data from IMPC.")
