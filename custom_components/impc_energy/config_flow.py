import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    ATTR_ACCOUNT_NAME,
    ATTR_ACCOUNT_NUMBER,
    ATTR_LOGIN_PAYLOAD,
    ATTR_PASSWORD,
    ATTR_TOKEN,
    ATTR_USERNAME,
    DOMAIN,
)
from .mdej_api import MdejAPI

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_USERNAME): cv.string,
        vol.Required(ATTR_PASSWORD): cv.string,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PASSWORD): cv.string,
    }
)


class IMPCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理 IMPC Energy 的配置流程。"""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """用户步骤：登录蒙电e家并为每个户号创建条目。"""
        errors = {}

        if user_input is not None:
            username = user_input[ATTR_USERNAME]
            password = user_input[ATTR_PASSWORD]

            try:
                api = MdejAPI(username)
                await api.initialize(username=username, pwd=password)
                users = await api.get_users()

                created_count = 0
                for user_info in users:
                    result = await self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "import"},
                        data={
                            ATTR_ACCOUNT_NUMBER: user_info[ATTR_ACCOUNT_NUMBER],
                            ATTR_ACCOUNT_NAME: user_info.get(ATTR_ACCOUNT_NAME),
                            ATTR_USERNAME: username,
                            ATTR_LOGIN_PAYLOAD: api.login_payload,
                            ATTR_TOKEN: api.token,
                        },
                    )
                    if result.get("type") == "create_entry":
                        created_count += 1

                if created_count == 0:
                    return self.async_abort(reason="already_configured")

                return self.async_abort(reason="initialization_completed")

            except Exception as err:
                _LOGGER.error("蒙电e家 登录或获取用户信息失败: %s", err)
                errors["base"] = "login_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, import_data=None) -> FlowResult:
        """内部步骤：根据户号创建单个配置条目。"""
        account_number = import_data[ATTR_ACCOUNT_NUMBER]
        account_name = import_data.get(ATTR_ACCOUNT_NAME) or account_number

        await self.async_set_unique_id(account_number)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="内蒙电网：" + account_name,
            data=import_data,
        )

    async def async_step_reauth(self, entry_data) -> FlowResult:
        """触发重新认证。"""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> FlowResult:
        """用户输入新密码后刷新 token。"""
        errors = {}

        if user_input is not None:
            username = self._reauth_entry.data[ATTR_USERNAME]
            password = user_input[ATTR_PASSWORD]

            try:
                api = MdejAPI(username)
                await api.initialize(username=username, pwd=password)

                target_entries = [
                    entry for entry in self.hass.config_entries.async_entries(DOMAIN)
                    if entry.data.get(ATTR_USERNAME) == username
                ]
                for entry in target_entries:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            ATTR_LOGIN_PAYLOAD: api.login_payload,
                            ATTR_TOKEN: api.token,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reauth_successful")

            except Exception as err:
                _LOGGER.error("蒙电e家重新认证失败: %s", err)
                errors["base"] = "login_failed"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )
