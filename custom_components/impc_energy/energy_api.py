import aiohttp
import logging

from homeassistant.const import (
    ATTR_NAME
)
from .const import (
    BASE_API_URL,
    ATTR_BALANCE
)

_LOGGER = logging.getLogger(__name__)


class EnergyAPI(object):
    def __init__(self, session: aiohttp.ClientSession, account_number):
        self._account_number = account_number
        self._account_name = None
        self._params = {
            "yhdabh": account_number
        }
        self.session = session

    timeout = aiohttp.ClientTimeout(total=60)
    header = {
        "Accept": "application/json, text/plain, */*",
        "appId": "wxb388e571f24e1111",
        "Accept-Language": "zh-CN,zh"
    }

    def set_account_name(self, account_name):
        self._account_name = account_name

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def account_name(self) -> str:
        return self._account_name

    async def get_basic(self):
        response = await self.session.get(BASE_API_URL + "/api/hlwyy/business-jffw/dldf/dldfList",
                                          timeout=EnergyAPI.timeout,
                                          params=self._params,
                                          headers=EnergyAPI.header)

        try:
            data = await response.json(encoding="utf-8")
            _LOGGER.info("基本信息: [{}]".format(data))

            return {
                ATTR_NAME: data["data"]["name"],
                ATTR_BALANCE: float(data["data"]["zmye"])
            }
        except:
            data = await response.text()
            _LOGGER.error("获取基本信息错误, res: [{}]".format(data))
