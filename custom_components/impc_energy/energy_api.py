import datetime

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
tz = datetime.timezone(datetime.timedelta(hours=+8))


class EnergyAPI(object):
    def __init__(self, session: aiohttp.ClientSession, account_number):
        self._account_number = account_number
        self._account_name = None
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
        param = {
            "yhdabh": self._account_number
        }
        response = await self.session.get(BASE_API_URL + "/api/hlwyy/business-jffw/dldf/dldfList",
                                          timeout=EnergyAPI.timeout,
                                          params=param,
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

    async def get_history(self, year: int):

        param = {
            "yhdabh": self._account_number,
            "fxny": year
        }
        response = await self.session.get(BASE_API_URL + "/api/hlwyy/business-jffw/dldf/zztList",
                                          timeout=EnergyAPI.timeout,
                                          params=param,
                                          headers=EnergyAPI.header)

        try:
            data = await response.json(encoding="utf-8")
            _LOGGER.info("历史数据: [{}]".format(data))

            return data["data"]
        except:
            data = await response.text()
            _LOGGER.error("获取历史数据错误, res: [{}]".format(data))

    async def get_history_data(self):

        now = datetime.datetime.now(tz)
        this_year = now.year
        this_month = now.month

        data_list = []
        last_year_data = await self.get_history(this_year - 1)

        # last year
        for i in range(12 - this_month + 1):
            month_str = "%d%02d" % (this_year - 1, i)
            data_list.append({
                "month": month_str,
                "bill": last_year_data["df"][i - 1],
                "consumption": last_year_data["dl"][i - 1]
            })

        if this_month > 1:
            this_year_data = await self.get_history(this_year)
            for i in range(this_month - 1):
                month_str = "%d%02d" % (this_year, i)
                data_list.append({
                    "month": month_str,
                    "bill": this_year_data["df"][i - 1],
                    "consumption": this_year_data["dl"][i - 1]
                })

        return data_list
