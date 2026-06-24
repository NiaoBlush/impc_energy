"""IMPC sensor platform."""

import datetime
import logging
from datetime import timedelta
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ACCOUNT_NAME,
    ATTR_ACCOUNT_NUMBER,
    ATTR_BALANCE,
    ATTR_BILL,
    ATTR_CONSUMPTION,
    ATTR_CURRENT,
    ATTR_CURRENT_PRICE,
    ATTR_CURRENT_TIER,
    ATTR_DAILY,
    ATTR_DATE,
    ATTR_DESC,
    ATTR_HISTORY,
    ATTR_MONTH,
    ATTR_PRICE_CODE,
    ATTR_PRICE_NAME,
    ATTR_QUERY_MONTH,
    ATTR_TIERS,
    ATTR_TOKEN,
    ATTR_TIERED_BILL,
    ATTR_TIER_SPREAD_BILL,
    ATTR_TOTAL_BILL,
    ATTR_TOTAL_CONSUMPTION,
    ATTR_USERNAME,
    DOMAIN,
    UNIT_CURRENCY_YUAN,
    UNIT_KILOWATT_HOUR,
)
from .mdej_api import MdejAPI

tz = datetime.timezone(timedelta(hours=+8))

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=8)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """通过配置条目设置传感器平台。"""
    _LOGGER.info("开始为实体设置传感器: %s", entry.entry_id)

    data = hass.data[DOMAIN].get(entry.entry_id, {})
    account_number = data.get(ATTR_ACCOUNT_NUMBER)
    account_name = data.get(ATTR_ACCOUNT_NAME)
    app_username = data.get(ATTR_USERNAME)
    app_token = data.get(ATTR_TOKEN)

    if not account_number or not app_username or not app_token:
        _LOGGER.warning(
            "Entry %s is missing required MDEJ configuration. "
            "This is usually an old config entry and should be re-added.",
            entry.entry_id,
        )
        return

    mdej_api = MdejAPI(app_username)
    await mdej_api.initialize(token=app_token)
    mdej_api.set_account_number(account_number)
    mdej_api.set_account_name(account_name)

    sensors = await get_sensors(mdej_api)
    async_add_entities(sensors, update_before_add=True)
    await _migrate_entity_ids(hass, sensors)


async def get_sensors(mdej_api: MdejAPI):
    """构造所有实体。"""
    return [
        ImpcBalanceSensor(mdej_api),
        ImpcHistorySensor(mdej_api),
        ImpcTieredBillSensor(mdej_api),
        MdejDailySensor(mdej_api),
    ]


async def _migrate_entity_ids(hass: HomeAssistant, sensors: list[Entity]) -> None:
    """将旧的基于名称的 entity_id 迁移到固定格式。"""
    entity_registry = er.async_get(hass)

    for sensor in sensors:
        unique_id = sensor.unique_id
        desired_entity_id = sensor.entity_id
        if not unique_id or not desired_entity_id:
            continue

        registry_entry = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if not registry_entry or registry_entry == desired_entity_id:
            continue

        try:
            entity_registry.async_update_entity(registry_entry, new_entity_id=desired_entity_id)
            _LOGGER.info("Migrated entity_id from %s to %s", registry_entry, desired_entity_id)
        except ValueError:
            _LOGGER.warning(
                "Unable to migrate entity_id from %s to %s because the target already exists.",
                registry_entry,
                desired_entity_id,
            )


class ImpcBalanceSensor(Entity):
    """电费余额。"""

    def __init__(self, mdej_api: MdejAPI):
        super().__init__()

        self._mdej_api = mdej_api
        self._name = f"电费余额_{mdej_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._mdej_api.account_number}_{ATTR_BALANCE}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._data = None
        self._attrs: Dict[str, Any] = {
            ATTR_ACCOUNT_NAME: mdej_api.account_name,
            ATTR_ACCOUNT_NUMBER: mdej_api.account_number,
            ATTR_DESC: "查询余额为结算系统余额=上月度结转电费+本月缴纳电费。实际电费余额以表计显示为准。"
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
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
            balance_info = await self._mdej_api.get_balance_info()
            self._state = self._data = balance_info[ATTR_BALANCE]
            self._attrs[ATTR_ACCOUNT_NAME] = self._mdej_api.account_name
            self._attrs["last_query"] = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            self._available = True
        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving balance data from MDEJ.")
        except Exception:
            self._available = False
            _LOGGER.exception("Error retrieving balance data from MDEJ.")


class ImpcHistorySensor(Entity):
    """历史电费电量。"""

    def __init__(self, mdej_api: MdejAPI):
        super().__init__()

        self._mdej_api = mdej_api
        self._name = f"历史电费_{mdej_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._mdej_api.account_number}_{ATTR_HISTORY}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._attrs = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
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
            history_data = await self._mdej_api.get_history_data()
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
            _LOGGER.exception("Error retrieving history data from MDEJ.")
        except Exception:
            self._available = False
            _LOGGER.exception("Error retrieving history data from MDEJ.")


class ImpcTieredBillSensor(Entity):
    """阶梯电费。"""

    def __init__(self, mdej_api: MdejAPI):
        super().__init__()

        self._mdej_api = mdej_api
        self._name = f"阶梯电费_{mdej_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._mdej_api.account_number}_{ATTR_TIERED_BILL}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._attrs: Dict[str, Any] = {
            ATTR_ACCOUNT_NAME: mdej_api.account_name,
            ATTR_ACCOUNT_NUMBER: mdej_api.account_number,
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    @property
    def available(self) -> bool:
        return self._available

    @property
    def state(self) -> Optional[float]:
        return self._state

    @property
    def icon(self):
        return "mdi:stairs"

    @property
    def unit_of_measurement(self):
        return UNIT_CURRENCY_YUAN

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    async def async_update(self):
        try:
            tiered_bill = await self._mdej_api.get_tiered_bill()
            self._state = tiered_bill[ATTR_TOTAL_BILL]
            self._attrs = {
                ATTR_ACCOUNT_NAME: self._mdej_api.account_name,
                ATTR_ACCOUNT_NUMBER: self._mdej_api.account_number,
                ATTR_QUERY_MONTH: tiered_bill[ATTR_QUERY_MONTH],
                ATTR_CURRENT_TIER: tiered_bill[ATTR_CURRENT_TIER],
                ATTR_CURRENT_PRICE: tiered_bill[ATTR_CURRENT_PRICE],
                ATTR_TOTAL_CONSUMPTION: tiered_bill[ATTR_TOTAL_CONSUMPTION],
                ATTR_TOTAL_BILL: tiered_bill[ATTR_TOTAL_BILL],
                ATTR_TIER_SPREAD_BILL: tiered_bill[ATTR_TIER_SPREAD_BILL],
                ATTR_PRICE_NAME: tiered_bill[ATTR_PRICE_NAME],
                ATTR_PRICE_CODE: tiered_bill[ATTR_PRICE_CODE],
                ATTR_TIERS: tiered_bill[ATTR_TIERS],
            }
            self._available = True
        except aiohttp.ClientError:
            self._available = False
            _LOGGER.exception("Error retrieving tiered bill data from MDEJ.")
        except Exception:
            self._available = False
            _LOGGER.exception("Error retrieving tiered bill data from MDEJ.")


class MdejDailySensor(Entity):
    """蒙电e家每日数据。"""

    def __init__(self, mdej_api: MdejAPI):
        super().__init__()

        self._mdej_api = mdej_api
        self._name = f"每日电量_{mdej_api.account_name}"
        self._attr_unique_id = f"{DOMAIN}_{self._mdej_api.account_number}_{ATTR_DAILY}_{ATTR_CONSUMPTION}"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._state = None
        self._available = False
        self._attrs = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
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
            _LOGGER.exception("Error retrieving daily data from MDEJ.")
        except Exception:
            self._available = False
            _LOGGER.exception("Error retrieving daily data from MDEJ.")
