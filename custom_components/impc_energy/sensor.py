"""GitHub sensor platform."""
import datetime
import logging

from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.const import (
    ATTR_NAME,
    CONF_NAME,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType
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
SCAN_INTERVAL = timedelta(hours=8)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ATTR_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_NAME): cv.string
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

    sensors = await get_sensors(energy_api, config)

    async_add_entities(sensors, update_before_add=True)


async def get_sensors(energy_api: EnergyAPI, config: ConfigType):
    basic_info = await energy_api.get_basic()
    account_name = basic_info[ATTR_NAME]
    energy_api.set_account_name(account_name)
    name_in_entity = config.get(CONF_NAME, account_name)

    sensors = [
        ImpcBalanceSensor(energy_api, name_in_entity),
        ImpcHistorySensor(energy_api, name_in_entity)
    ]

    return sensors


class ImpcBaseSensor(SensorEntity):
    def __init__(self, energy_api: EnergyAPI, name: str, sensor_type: str):
        self._energy_api = energy_api
        self._name = f"{name}_{sensor_type}"
        self._state = None
        self._available = False
        self._attrs: Dict[str, Any] = {}
        self._unique_id = f"{DOMAIN}_{self._energy_api.account_number}_{sensor_type}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._energy_api.account_number)},
            name=f"IMPC Account {self._energy_api.account_number}",
            manufacturer="IMPC",
            model="Energy Account",
        )

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs


class ImpcBalanceSensor(ImpcBaseSensor):
    def __init__(self, energy_api: EnergyAPI, name):
        super().__init__(energy_api, name, "电费余额")
        self._attrs.update({
            "account_name": energy_api.account_name,
            "account_number": energy_api.account_number,
            "desc": "查询余额为结算系统余额=上月度结转电费+本月缴纳电费。实际电费余额以表计显示为准"
        })

    @property
    def icon(self):
        return "mdi:cash-100"

    @property
    def native_value(self) -> Optional[float]:
        return self._state

    @property
    def native_unit_of_measurement(self):
        return '元'

    async def async_update(self):
        try:
            basic_data = await self._energy_api.get_basic()
            self._state = basic_data[ATTR_BALANCE]
            self._attrs["last_query"] = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            self._available = True
        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving data from IMPC.")


class ImpcHistorySensor(ImpcBaseSensor):
    def __init__(self, energy_api: EnergyAPI, name):
        super().__init__(energy_api, name, "历史")

    @property
    def icon(self):
        return "mdi:flash"

    @property
    def native_value(self) -> Optional[str]:
        return self._state

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
