import datetime
import asyncio

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
        "Accept-Language": "zh-CN,zh",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.55(0x1800372d) NetType/WIFI Language/zh_CN",
        "qdly": "WECHAT"
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
        """
        获取基本信息 (dldfList)
        包括zmye及账户名(未脱敏住址)

        res:
        {
            "code": 0,
            "data": {
                "qjwyj": "0",
                "zmye": "888.88",
                "d_date": "2025-02-08 11:06:54",
                "name": "某小区某号楼某单元某层东",
                "qjdf": "0"
            }
        }

        """
        param = {
            "yhdabh": self._account_number
        }
        response = await self.session.get(BASE_API_URL + "/api/hlwyy/business-jffw/dldf/dldfList",
                                          timeout=EnergyAPI.timeout,
                                          params=param,
                                          headers=EnergyAPI.header)

        try:
            data = await response.json(encoding="utf-8")
            _LOGGER.info("基本信息(dldfList): [{}]".format(data))

            return {
                ATTR_NAME: data["data"]["name"],
                # 余额采用get_basic_new中的syje, 所以这个方法不再返回剩余金额
                # ATTR_BALANCE: float(data["data"]["zmye"])
            }
        except:
            data = await response.text()
            _LOGGER.error("获取基本信息(dldfList)错误, res: [{}]".format(data))

    async def get_history(self, year: int):
        """
        获取电量电费列表
        :param year: 某年
        res:
        {
            "code": 0,
            "data": {
                "df": [
                    85.9,
                    91.94,
                    80.78,
                    110.08,
                    82.64,
                    84.5,
                    118.12,
                    97.52,
                    103.57,
                    89.62,
                    96.59,
                    136.71,
                    0
                ],
                "dl": [
                    203,
                    216,
                    192,
                    255,
                    196,
                    200,
                    268,
                    228,
                    241,
                    211,
                    226,
                    294,
                    0
                ],
                "bqdl": "0.00",
                "yf": [
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    7,
                    8,
                    9,
                    10,
                    11,
                    12,
                    12
                ],
                "bqdf": "0.00"
            }
        }


        """

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

        # 本期
        data_list.append({
            "month": "current",
            "bill": last_year_data["df"][-1],
            "consumption": last_year_data["dl"][-1]
        })

        # last year
        for i in range(this_month, 13):
            month_str = "%d%02d" % (this_year - 1, i)
            data_list.append({
                "month": month_str,
                "bill": last_year_data["df"][i - 1],
                "consumption": last_year_data["dl"][i - 1]
            })

        await asyncio.sleep(5)

        if this_month > 1:
            this_year_data = await self.get_history(this_year)
            for i in range(1, this_month):
                month_str = "%d%02d" % (this_year, i)
                data_list.append({
                    "month": month_str,
                    "bill": this_year_data["df"][i - 1],
                    "consumption": this_year_data["dl"][i - 1]
                })

        return data_list

    async def get_basic_new(self):
        """
        获取基本信息 (queryDfInfoNew)
        包含syje与脱敏地址

        res:
        {
            "code": 0,
            "data": {
                "gsbh": "01",
                "limitFlag": "02",
                "qjwyj": "0.0",
                "syje": "888.88",
                "name": "某****某层东",
                "addr": "******某层东",
                "khxzmc": "城镇居民生活用电",
                "sfyxjf": "01"
            }
        }

        :return:
        """

        param = {
            "yhdabh": self._account_number
        }
        response = await self.session.get(BASE_API_URL + "/api/hlwyy/business-jffw/znjf/queryDfInfoNew",
                                          timeout=EnergyAPI.timeout,
                                          params=param,
                                          headers=EnergyAPI.header)

        try:
            data = await response.json(encoding="utf-8")
            _LOGGER.info("基本信息(queryDfInfoNew): [{}]".format(data))

            return {
                # 这个接口返回的地址是脱敏后的地址, 所以方法不返回地址, 采用get_basic返回的地址
                ATTR_BALANCE: float(data["data"]["syje"])
            }
        except:
            data = await response.text()
            _LOGGER.error("获取基本信息(queryDfInfoNew)错误, res: [{}]".format(data))
