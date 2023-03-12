import aiohttp
import logging
import json
from .const import BASE_API_URL

_LOGGER = logging.getLogger(__name__)


class EnergyAPI(object):
    def __init__(self, session: aiohttp.ClientSession, account_number):
        self.account_number = account_number
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

    async def get_basic(self):
        response = await self.session.get(BASE_API_URL + "/api/hlwyy/business-jffw/dldf/dldfList",
                                          timeout=EnergyAPI.timeout,
                                          params=self._params,
                                          headers=EnergyAPI.header)

        try:
            data = await response.json(encoding="utf-8")
            _LOGGER.error("基本信息: [{}]".format(data))

            return {
                "name": data["data"]["name"],
                "balance": data["data"]["zmye"]
            }
        except:
            _LOGGER.error("获取基本信息错误, res: [{}]".format(response))
