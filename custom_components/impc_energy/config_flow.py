import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN,
    ATTR_ACCOUNT_DATA,
    ATTR_ACCOUNT_NAME,
    ATTR_ACCOUNT_NUMBER,
    ATTR_CONFIG_MDEJ,
    ATTR_USERNAME,
    ATTR_PASSWORD,
    ATTR_TOKEN,
    ATTR_LOGIN_PAYLOAD
)
from .energy_api import EnergyAPI
from .mdej_api import MdejAPI

_LOGGER = logging.getLogger(__name__)

# 配置用户输入的字段
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCOUNT_NUMBER): cv.string,
        vol.Optional(ATTR_ACCOUNT_NAME): cv.string,
        vol.Optional(ATTR_CONFIG_MDEJ, default=True): cv.boolean,
    }
)
# 蒙电e家字段
STEP_MDEJ_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_USERNAME): cv.string,
        vol.Required(ATTR_PASSWORD): cv.string,
    }
)


class IMPCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理 IMPC Energy 的配置流程。"""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """用户步骤：获取账号配置。"""
        errors = {}

        if user_input is not None:
            # 如果用户提供了 account_name，则直接使用；如果没有提供，则调用 API 获取
            account_number = user_input[ATTR_ACCOUNT_NUMBER]
            account_name = user_input.get(ATTR_ACCOUNT_NAME)

            # 如果没有提供 account_name，调用 EnergyAPI 获取
            if not account_name:
                try:
                    # 直接使用导入的 async_get_clientsession 获取 session
                    session = async_get_clientsession(self.hass)
                    api = EnergyAPI(session, account_number)
                    basic_info = await api.get_basic()  # 获取账户基本信息

                    # 如果成功获取账户名
                    account_name = basic_info.get("name", None)
                    _LOGGER.info(f"获取到账户名: {account_name}")

                    if account_name:
                        user_input[ATTR_ACCOUNT_NAME] = account_name
                    else:
                        errors[ATTR_ACCOUNT_NAME] = "无法从互联网获取账户名，请手动输入"
                except Exception as e:
                    # 如果 API 请求失败
                    _LOGGER.error(f"获取账户名失败: {e}")
                    errors[ATTR_ACCOUNT_NAME] = "无法从互联网获取账户名，请手动输入"

            # 如果一切正常，创建配置条目
            if not errors:
                await self.async_set_unique_id(account_number)
                self._abort_if_unique_id_configured()

                if user_input[ATTR_CONFIG_MDEJ]:
                    # 如果选择继续配置蒙电e家
                    self.context[ATTR_ACCOUNT_DATA] = user_input
                    return await self.async_step_mdej()
                else:
                    return self.async_create_entry(
                        title="内蒙电网：" + account_name,
                        data=user_input,
                    )

        # 返回一个配置表单，显示描述信息并处理错误
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )

    async def async_step_mdej(self, user_input=None) -> FlowResult:
        """配置蒙电e家账户信息"""
        errors = {}

        if user_input is not None:
            username = user_input[ATTR_USERNAME]
            password = user_input[ATTR_PASSWORD]

            try:
                api = MdejAPI(username)
                await api.initialize(username=username, pwd=password)
                login_payload = api.login_payload
                app_token = api.token

                account_data = self.context[ATTR_ACCOUNT_DATA]
                entry_data = {
                    **account_data,
                    ATTR_USERNAME: username,
                    ATTR_LOGIN_PAYLOAD: login_payload,
                    ATTR_TOKEN: app_token
                }

                return self.async_create_entry(
                    title="内蒙电网：" + account_data[ATTR_ACCOUNT_NAME],
                    data=entry_data,
                )

            except Exception as e:
                _LOGGER.error(f"蒙电e家 登录失败: {e}")
                errors["base"] = "登录失败"

        return self.async_show_form(
            step_id="mdej",
            data_schema=STEP_MDEJ_DATA_SCHEMA,
            errors=errors
        )
