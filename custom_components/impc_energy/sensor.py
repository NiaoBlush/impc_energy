"""GitHub sensor platform."""
import datetime
import logging

from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_NAME
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from .energy_api import EnergyAPI

from .const import (
    DOMAIN,
    ATTR_BALANCE,
    ATTR_ACCOUNT_NUMBER
)

tz = datetime.timezone(timedelta(hours=+8))

_LOGGER = logging.getLogger(__name__)

# Time between updating data
SCAN_INTERVAL = timedelta(days=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_ACCOUNT_NUMBER): cv.string,
        vol.Optional(ATTR_NAME): cv.string
    }
)


async def get_sensors(energy_api: EnergyAPI, config: ConfigType):
    basic_info = await energy_api.get_basic()
    account_name = basic_info[ATTR_NAME]
    energy_api.set_account_name(account_name)
    name_in_entity = config[ATTR_NAME] if config.__contains__(ATTR_NAME) else account_name

    sensors = []
    sensors.append(ImpcBalanceSensor(energy_api, name_in_entity))
    sensors.append(ImpcHistorySensor(energy_api, name_in_entity))

    return sensors


async def async_setup_platform(
        hass: HomeAssistantType,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    energy_api = EnergyAPI(session, config[ATTR_ACCOUNT_NUMBER])

    sensors = await get_sensors(energy_api, config)

    async_add_entities(sensors, update_before_add=True)

    metadata = {
        "source": DOMAIN,
        "statistic_id": f"{DOMAIN}:energy_consumption",
        "unit_of_measurement": "kWh",
        "has_mean": False,
        "has_sum": True,
    }
    statistics = [
        {'start': datetime.datetime(2023, 1, 1, 0, 0), 'sum': 200},
        {'start': datetime.datetime(2023, 2, 1, 0, 0), 'sum': 209},
        {'start': datetime.datetime(2023, 3, 1, 0, 0), 'sum': 241},
        {'start': datetime.datetime(2023, 4, 1, 0, 0), 'sum': 377},
        {'start': datetime.datetime(2023, 5, 1, 0, 0), 'sum': 262},
        {'start': datetime.datetime(2023, 6, 1, 0, 0), 'sum': 187},
        {'start': datetime.datetime(2023, 7, 1, 0, 0), 'sum': 124},
        {'start': datetime.datetime(2023, 8, 1, 0, 0), 'sum': 313},
        {'start': datetime.datetime(2023, 9, 1, 0, 0), 'sum': 207},
        {'start': datetime.datetime(2023, 10, 1, 0, 0), 'sum': 300},
        {'start': datetime.datetime(2023, 11, 1, 0, 0), 'sum': 118},
        {'start': datetime.datetime(2023, 12, 1, 0, 0), 'sum': 289}
    ]
    async_add_external_statistics(hass, metadata, statistics)


class ImpcBalanceSensor(Entity):
    def __init__(self, energy_api: EnergyAPI, name):
        super().__init__()

        self._energy_api = energy_api
        self._name = f"{name}_电费余额"
        self._state = None
        self._available = False
        self._data = None
        self._attrs: Dict[str, Any] = {
            "account_name": energy_api.account_name,
            "account_number": energy_api.account_number,
            "desc": "查询余额为结算系统余额=上月度结转电费+本月缴纳电费。实际电费余额以表计显示为准"
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_id(self) -> str:
        return f"sensor.{DOMAIN}_{self._energy_api.account_number}_{ATTR_BALANCE}"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def icon(self):
        return "hass:cash-100"

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def data(self) -> Optional[float]:
        return self._data

    @property
    def unit_of_measurement(self):
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


class ImpcHistorySensor(Entity):
    def __init__(self, energy_api: EnergyAPI, name):
        super().__init__()

        self._energy_api = energy_api
        self._name = f"{name}_历史"
        self._state = None
        self._available = False
        self._data = None
        self._attrs = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_id(self) -> str:
        return f"sensor.{DOMAIN}_{self._energy_api.account_number}_history"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def icon(self):
        return "hass:flash"

    # @property
    # def data(self) -> Optional[float]:
    #     return self._data

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    async def async_update(self):
        try:

            self._state = "history"
            history_data = await self._energy_api.get_history_data()
            self._attrs = {}
            for item in history_data:
                self._attrs[item["month"]] = {
                    "bill": item["bill"],
                    "consumption": item["consumption"]
                }

            self._available = True



        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving data from IMPC.")
