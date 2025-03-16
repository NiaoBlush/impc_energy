"""GitHub sensor platform."""
import datetime
import logging

from datetime import timedelta
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.core import (
    HomeAssistant
)
from .energy_api import EnergyAPI
from .mdej_api import MdejAPI

from .const import (
    DOMAIN,
    ATTR_ACCOUNT_NAME,
    ATTR_ACCOUNT_NUMBER,
    ATTR_BALANCE,
    ATTR_BILL,
    ATTR_CONSUMPTION,
    ATTR_CURRENT,
    ATTR_DAILY,
    ATTR_DATE,
    ATTR_DESC,
    ATTR_HISTORY,
    ATTR_MONTH,
    ATTR_TOKEN,
    ATTR_USERNAME,
    UNIT_CURRENCY_YUAN,
    UNIT_KILOWATT_HOUR,
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
    _LOGGER.info("开始为实体设置传感器: %s", entry.entry_id)

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
    energy_api.set_account_name(account_name)

    # 获取app信息
    app_username = data.get(ATTR_USERNAME)
    app_token = data.get(ATTR_TOKEN)
    # 创建 MdejAPI 实例
    mdej_api = None
    if app_username and app_token:
        mdej_api = MdejAPI(app_username)
        await mdej_api.initialize(token=app_token)
        mdej_api.set_account_number(account_number)
        mdej_api.set_account_name(account_name)

    sensors = await get_sensors(energy_api, mdej_api)
    async_add_entities(sensors, update_before_add=True)


async def get_sensors(energy_api: EnergyAPI, mdej_api: MdejAPI):
    sensors = []

    # 公众号数据传感器
    sensors.append(ImpcBalanceSensor(energy_api))
    sensors.append(ImpcHistorySensor(energy_api))

    if mdej_api:
        # 蒙电e家传感器
        sensors.append(MdejDailySensor(mdej_api))

    return sensors


class ImpcBalanceSensor(Entity):
    def __init__(self, energy_api: EnergyAPI):
        super().__init__()

        self._energy_api = energy_api
        self._name = f"电费余额_{energy_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._energy_api.account_number}_{ATTR_BALANCE}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._data = None
        self._attrs: Dict[str, Any] = {
            ATTR_ACCOUNT_NAME: energy_api.account_name,
            ATTR_ACCOUNT_NUMBER: energy_api.account_number,
            ATTR_DESC: "查询余额为结算系统余额=上月度结转电费+本月缴纳电费。实际电费余额以表计显示为准。"
        }

        _LOGGER.debug(f"ImpcBalanceSensor unique id: {self._attr_unique_id}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        # 使用 account_number 生成唯一标识符
        return self._attr_unique_id

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
        return UNIT_CURRENCY_YUAN

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
    def __init__(self, energy_api: EnergyAPI):
        super().__init__()

        self._energy_api = energy_api
        self._name = f"历史电费_{energy_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._energy_api.account_number}_{ATTR_HISTORY}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._data = None
        self._attrs = None

        _LOGGER.debug(f"ImpcHistorySensor unique id: {self._attr_unique_id}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        # 使用 account_number 生成唯一标识符
        return self._attr_unique_id

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
    def unit_of_measurement(self):
        return UNIT_CURRENCY_YUAN

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    async def async_update(self):
        try:

            history_data = await self._energy_api.get_history_data()
            self._attrs = {}
            for item in history_data[ATTR_HISTORY]:
                self._attrs[item[ATTR_MONTH]] = {
                    ATTR_BILL: item[ATTR_BILL],
                    ATTR_CONSUMPTION: item[ATTR_CONSUMPTION]
                }
            self._attrs[ATTR_CURRENT] = {
                ATTR_BILL: history_data[ATTR_CURRENT][ATTR_BILL],
                ATTR_CONSUMPTION: history_data[ATTR_CURRENT][ATTR_CONSUMPTION]
            }
            self._state = history_data[ATTR_CURRENT][ATTR_BILL]

            self._available = True

        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("从IMPC获取数据失败")


class MdejDailySensor(Entity):
    """蒙电e家每日数据"""

    def __init__(self, mdej_api: MdejAPI):
        super().__init__()

        self._mdej_api = mdej_api
        self._name = f"每日电量_{mdej_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._mdej_api.account_number}_{ATTR_DAILY}_{ATTR_CONSUMPTION}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._data = None
        self._attrs = None

        _LOGGER.debug(f"MdejDailySensor unique id: {self._attr_unique_id}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        # 使用 account_number 生成唯一标识符
        return self._attr_unique_id

    @property
    def available(self) -> bool:
        return self._available

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def icon(self):
        return "mdi:calendar-month-outline"

    @property
    def unit_of_measurement(self):
        return UNIT_KILOWATT_HOUR

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    async def async_update(self):
        try:

            daily_data = await self._mdej_api.get_daily()
            self._attrs = {}
            for item in daily_data:
                self._attrs[item[ATTR_DATE]] = item[ATTR_CONSUMPTION]

            self._state = daily_data[-1][ATTR_CONSUMPTION]

            self._available = True

        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("从MDEJ获取数据失败")
