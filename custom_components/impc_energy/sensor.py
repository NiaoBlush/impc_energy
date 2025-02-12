"""GitHub sensor platform."""
import datetime
import logging

from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import aiohttp
from homeassistant.const import (
    ATTR_NAME
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType
)
from homeassistant.core import (
    HomeAssistant
)
from .energy_api import EnergyAPI

from .const import (
    DOMAIN,
    ATTR_BALANCE,
    ATTR_HISTORY,
    ATTR_ACCOUNT_NUMBER,
    ATTR_ACCOUNT_NAME,
    ATTR_DESC,
    ATTR_BILL,
    ATTR_CONSUMPTION
)

tz = datetime.timezone(timedelta(hours=+8))

_LOGGER = logging.getLogger(__name__)

# Time between updating data
SCAN_INTERVAL = timedelta(hours=8)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """通过配置条目设置传感器平台。"""
    _LOGGER.debug("Setting up sensor for entry: %s", entry.entry_id)

    # 获取账户信息
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    account_number = data.get(ATTR_ACCOUNT_NUMBER)
    account_name = data.get(ATTR_ACCOUNT_NAME)

    if not account_number:
        _LOGGER.error("Missing account_number in entry data")
        return

    # 创建 EnergyAPI 实例
    session = async_get_clientsession(hass)
    energy_api = EnergyAPI(session, account_number)
    sensors = await get_sensors(energy_api, account_name)

    async_add_entities(sensors, update_before_add=True)


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
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    energy_api = EnergyAPI(session, config[ATTR_ACCOUNT_NUMBER])

    sensors = await get_sensors(energy_api, config)

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
            ATTR_ACCOUNT_NAME: energy_api.account_name,
            ATTR_ACCOUNT_NUMBER: energy_api.account_number,
            ATTR_DESC: "查询余额为结算系统余额=上月度结转电费+本月缴纳电费。实际电费余额以表计显示为准"
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        # 使用 account_number 生成唯一标识符
        return f"{DOMAIN}_{self._energy_api.account_number}_{ATTR_BALANCE}"

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

            basic_data = await self._energy_api.get_basic_new()
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
    def unique_id(self) -> str:
        # 使用 account_number 生成唯一标识符
        return f"{DOMAIN}_{self._energy_api.account_number}_{ATTR_HISTORY}"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def icon(self):
        return "hass:flash"

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
                    ATTR_BILL: item["bill"],
                    ATTR_CONSUMPTION: item["consumption"]
                }

            self._available = True

        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving data from IMPC.")
