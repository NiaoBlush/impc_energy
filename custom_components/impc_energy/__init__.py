import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import (
    DOMAIN,
    ATTR_ACCOUNT_NAME,
    ATTR_ACCOUNT_NUMBER,
    ATTR_USERNAME,
    ATTR_PASSWORD,
    ATTR_TOKEN,
    ATTR_LOGIN_PAYLOAD
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """当配置条目被创建时被调用。"""
    _LOGGER.debug("Setting up entry: %s", entry.data)

    # 获取账户信息
    account_number = entry.data[ATTR_ACCOUNT_NUMBER]
    account_name = entry.data.get(ATTR_ACCOUNT_NAME)
    app_username = entry.data.get(ATTR_USERNAME)
    app_login_payload = entry.data.get(ATTR_LOGIN_PAYLOAD)
    app_token = entry.data.get(ATTR_TOKEN)

    # 存储配置信息到 hass.data
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        ATTR_ACCOUNT_NUMBER: account_number,
        ATTR_ACCOUNT_NAME: account_name,
        ATTR_USERNAME: app_username,
        ATTR_LOGIN_PAYLOAD: app_login_payload,
        ATTR_TOKEN: app_token
    }

    # 加载平台
    try:
        # 通过 async_setup_platforms 来加载平台
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])  # 加载传感器平台
    except Exception as e:
        _LOGGER.error(f"加载平台时出错: {e}")
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """当用户删除集成时调用，用于清理和卸载平台。"""
    _LOGGER.debug("Unloading entry: %s", entry.data)

    # 卸载平台（例如 sensor）
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])  # 卸载传感器平台

    # 清理存储的数据
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id)

    return True
