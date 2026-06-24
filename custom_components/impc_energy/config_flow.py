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
        vol.Optional(ATTR_ACCOUNT_NAME): cv.string,
    }
)


class IMPCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理 IMPC Energy 的配置流程。"""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """用户步骤：使用蒙电e家账号自动获取户号并创建配置。"""
        errors = {}

        if user_input is not None:
            username = user_input[ATTR_USERNAME]
            password = user_input[ATTR_PASSWORD]
            account_name = user_input.get(ATTR_ACCOUNT_NAME)

            try:
                api = MdejAPI(username)
                await api.initialize(username=username, pwd=password)
                user_info = await api.get_user()

                account_number = user_info[ATTR_ACCOUNT_NUMBER]
                if not account_name:
                    account_name = user_info.get(ATTR_ACCOUNT_NAME)

                if not account_name:
                    raise ValueError("未能从蒙电e家获取地址，请手动填写账户名称")

                await self.async_set_unique_id(account_number)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="内蒙电网：" + account_name,
                    data={
                        ATTR_ACCOUNT_NUMBER: account_number,
                        ATTR_ACCOUNT_NAME: account_name,
                        ATTR_USERNAME: username,
                        ATTR_LOGIN_PAYLOAD: api.login_payload,
                        ATTR_TOKEN: api.token,
                    },
                )

            except ValueError as err:
                _LOGGER.error("配置失败: %s", err)
                errors[ATTR_ACCOUNT_NAME] = "无法自动获取地址，请手动填写"
            except Exception as err:
                _LOGGER.error("蒙电e家 登录或获取用户信息失败: %s", err)
                errors["base"] = "登录失败"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
