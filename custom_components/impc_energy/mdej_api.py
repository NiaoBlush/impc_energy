"""蒙电e家 API。"""

import datetime
import aiohttp
import asyncio
import logging

from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Util.Padding import pad
import base64
import json

from .const import (
    BASE_APP_API_URL,
    ATTR_ACCOUNT_NAME,
    ATTR_ACCOUNT_NUMBER,
    ATTR_BALANCE,
    ATTR_BILL,
    ATTR_CURRENT,
    ATTR_CURRENT_PRICE,
    ATTR_CURRENT_TIER,
    ATTR_DATE,
    ATTR_CONSUMPTION,
    ATTR_HISTORY,
    ATTR_MONTH,
    ATTR_PRICE,
    ATTR_PRICE_CODE,
    ATTR_PRICE_NAME,
    ATTR_QUERY_MONTH,
    ATTR_TIER,
    ATTR_TIER_NAME,
    ATTR_TIERS,
    ATTR_TIER_SPREAD_BILL,
    ATTR_TOTAL_BILL,
    ATTR_TOTAL_CONSUMPTION,
)

_LOGGER = logging.getLogger(__name__)
tz = datetime.timezone(datetime.timedelta(hours=+8))


class MdejAuthError(Exception):
    """蒙电e家认证失败。"""


class MdejAPI(object):
    TIER_NAME_MAP = {
        1: "第一阶梯",
        2: "第二阶梯",
        3: "第三阶梯",
    }

    def __init__(self, username):
        self._username = username
        self._account_number = None
        self._account_name = None
        self._encrypted_account_number = None
        self._public_key = None
        self._login_payload = None
        self._token = None

    timeout = aiohttp.ClientTimeout(total=30)
    header = {
        "Host": "mdej.impc.com.cn",
        "qdly": "MDEJ",
        "Accept": "*/*",
        "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
        "Proxy-Connection": "keep-alive",
        "Access-Control-Max-Age": "86400",
        "Access-Control-Allow-Headers": "appId",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Html5Plus/1.0 (Immersed/20) uni-app",
        "Connection": "keep-alive"
    }

    @property
    def login_payload(self) -> str:
        return self._login_payload

    @property
    def token(self) -> str:
        return self._token

    @property
    def account_name(self) -> str:
        return self._account_name

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def encrypted_account_number(self) -> str:
        return self._encrypted_account_number

    def set_account_number(self, account_number):
        """
        设置户号
        部分接口需要户号参数
        """
        self._account_number = account_number
        self._encrypted_account_number = self.encrypt_account_number(account_number)

    def set_account_name(self, account_name):
        self._account_name = account_name

    def get_header_with_token(self):
        """
        获取添加token的请求头
        """
        return {
            **MdejAPI.header,
            "hlwyy-Token": self._token
        }

    @staticmethod
    def _raise_if_auth_failed(resp_json):
        """在服务端明确返回认证问题时抛出认证异常。"""
        if resp_json.get("code") == 2:
            raise MdejAuthError(f"认证失败, 响应: {resp_json}")

    @staticmethod
    def _safe_int(value, default=0):
        """将接口字段安全转换为整数。"""
        if value in (None, ""):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value, default=0.0):
        """将接口字段安全转换为浮点数。"""
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    async def initialize(self, username=None, pwd=None, login_payload=None, token=None):
        """
        初始化 需要手动调用
        获取公钥, 登录

        使用login_payload初始化时必报错, 原因未知
        :return:
        """
        if token:
            _LOGGER.debug("使用token初始化")
            self._token = token
        else:
            await self._get_public_key()
            if login_payload is None:
                if username is None or pwd is None:
                    raise ValueError("必须提供用户名和密码，或者直接提供 payload")
                _LOGGER.debug("使用用户名密码初始化")
                login_payload = self.cal_payload(username, pwd)
            self._login_payload = login_payload
            _LOGGER.debug("使用login payload初始化")
            self._token = await self.get_token(self._login_payload)

    async def _get_public_key(self):
        _LOGGER.debug("开始获取公钥")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        f"{BASE_APP_API_URL}/hlwyy/business-zhfw/account/key",
                        timeout=MdejAPI.timeout,
                        headers=MdejAPI.header
                ) as response:

                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("获取公钥失败, 状态码: [%d], 响应: [%s]", response.status, text)
                        return None

                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)
                    pub_key = resp_json.get("data")

                    if not pub_key:
                        _LOGGER.error("获取公钥失败, 未获取到 pub_key, 响应: [%s]", resp_json)
                        return None

                    _LOGGER.info("获取公钥成功: [%s...]", pub_key[:10])
                    self._public_key = pub_key

            except Exception as e:
                _LOGGER.error("获取公钥请求异常,  错误: [%s]", str(e))
                return None

    def _get_pub_key_pem(self):
        if not self._public_key:
            return None
        else:
            return "\n".join([
                "-----BEGIN PUBLIC KEY-----",
                self._public_key,
                "-----END PUBLIC KEY-----"
            ])

    def cal_payload(self, username, pwd):
        """
        计算登录时要携带的payload
        :param username: 用户名
        :param pwd: 密码 明文
        :return: payload
        """

        data_to_encrypt = {
            "lxdh": username,
            "dlkl": username,
            "dlmm": pwd,
            "qdly": "APP",
            "version": "3.1.3"
        }
        plaintext = json.dumps(data_to_encrypt).encode('utf-8')

        pub_key_str = self._get_pub_key_pem()
        pub_key = RSA.importKey(pub_key_str)
        cipher = PKCS1_v1_5.new(pub_key)

        encrypted_bytes = cipher.encrypt(plaintext)
        encrypted_base64_str = base64.b64encode(encrypted_bytes).decode('utf-8')
        _LOGGER.debug("得到登录payload: [%s...]", encrypted_base64_str[:10])

        return encrypted_base64_str

    @staticmethod
    def encrypt_account_number(account_number: str) -> str:
        """使用 AES-128-ECB-PKCS7 加密户号并返回 Base64。"""
        key = b"nmdlyx1234567890"
        cipher = AES.new(key, AES.MODE_ECB)
        encrypted_bytes = cipher.encrypt(pad(account_number.encode("utf-8"), AES.block_size))
        return base64.b64encode(encrypted_bytes).decode("utf-8")

    async def get_token(self, payload):
        """
        登录以获取 token
        这个接口不稳定, 即使是在手机上偶尔也会报500
        :param payload: 登录请求负载
        :return: token (str)
        :raises Exception: 登录失败时抛出异常
        """
        data = {
            "payLoad": payload,
            "publicKey": self._public_key
        }
        _LOGGER.info("开始登录 app, 用户: [%s]", self._username)
        await asyncio.sleep(1)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                        f"{BASE_APP_API_URL}/hlwyy/business-zhfw/account/loginNew3",
                        timeout=MdejAPI.timeout,
                        json=data,
                        headers=MdejAPI.header
                ) as response:

                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("登录失败, 用户: [%s], 状态码: [%d], 响应: [%s]", self._username, response.status, text)
                        raise Exception(f"用户 [{self._username}] 登录失败: HTTP 状态码 {response.status}, 响应: {text}")

                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)

                    if resp_json.get("code") != 0:
                        _LOGGER.error("登录失败, 用户: [%s], code != 0, 响应: [%s]", self._username, resp_json)
                        raise Exception(f"用户 [{self._username}] 登录失败: code != 0, 响应: {resp_json}")

                    token = resp_json.get("data", {}).get("token")

                    if not token:
                        _LOGGER.error("登录失败, 用户: [%s], 未获取到 token, 响应: [%s]", self._username, resp_json)
                        raise Exception(f"用户 [{self._username}] 登录失败: 未获取到 token, 响应: {resp_json}")

                    _LOGGER.info("登录成功, 用户: [%s]", self._username)
                    self._token = token
                    return token

            except Exception as e:
                _LOGGER.error("登录请求异常, 用户: [%s], 错误: [%s]", self._username, str(e))
                raise

    async def get_user(self):
        """获取用户绑定信息，并使用首个返回记录设置户号和地址。"""
        users = await self.get_users()
        user_info = users[0]
        self.set_account_number(user_info[ATTR_ACCOUNT_NUMBER])
        if user_info.get(ATTR_ACCOUNT_NAME):
            self.set_account_name(user_info[ATTR_ACCOUNT_NAME])
        return user_info

    async def get_users(self):
        """获取用户绑定信息列表。"""
        _LOGGER.info("开始获取用户绑定信息, 用户: [%s]", self._username)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        f"{BASE_APP_API_URL}/hlwyy/business-ggfw/communal/getUser",
                        timeout=MdejAPI.timeout,
                        headers=self.get_header_with_token()
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"获取用户信息失败: HTTP 状态码 {response.status}, 响应: {text}")

                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)
                    if resp_json.get("code") != 0:
                        raise Exception(f"获取用户信息失败: code != 0, 响应: {resp_json}")

                    raw_user_list = resp_json.get("data") or []
                    if not raw_user_list:
                        raise Exception(f"获取用户信息失败: 未获取到用户数据, 响应: {resp_json}")

                    users = []
                    for user_info in raw_user_list:
                        account_number = user_info.get("yhdabh")
                        account_name = user_info.get("yhmc")
                        if not account_number:
                            continue
                        users.append({
                            ATTR_ACCOUNT_NUMBER: account_number,
                            ATTR_ACCOUNT_NAME: account_name,
                        })

                    if not users:
                        raise Exception(f"获取用户信息失败: 未获取到有效户号, 响应: {resp_json}")

                    return users

            except Exception as e:
                _LOGGER.error("获取用户绑定信息异常, 用户: [%s], 错误: [%s]", self._username, str(e))
                raise

    async def get_balance_info(self):
        """获取电费余额信息。"""
        if not self._encrypted_account_number:
            raise ValueError("必须先设置 account_number，才能获取电费信息")

        params = {
            "yhdabh": self._encrypted_account_number,
        }
        _LOGGER.info("开始获取电费信息, 户号: [%s]", self._account_number)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        f"{BASE_APP_API_URL}/hlwyy/business-jffw/znjf/queryDfInfoNew_new",
                        timeout=MdejAPI.timeout,
                        params=params,
                        headers=self.get_header_with_token()
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"获取电费信息失败: HTTP 状态码 {response.status}, 响应: {text}")

                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)
                    if resp_json.get("code") != 0:
                        raise Exception(f"获取电费信息失败: code != 0, 响应: {resp_json}")

                    data = resp_json.get("data") or {}
                    if "syje" not in data:
                        raise Exception(f"获取电费信息失败: 未获取到余额字段, 响应: {resp_json}")

                    return {
                        ATTR_BALANCE: float(data["syje"]),
                        ATTR_ACCOUNT_NAME: self._account_name,
                    }

            except Exception as e:
                _LOGGER.error("获取电费信息异常, 户号: [%s], 错误: [%s]", self._account_number, str(e))
                raise

    async def get_history(self, year: int):
        """获取指定年份的电量电费列表。"""
        if not self._account_number:
            raise ValueError("必须先设置 account_number，才能获取历史电费电量")

        params = {
            "yhdabh": self._account_number,
            "fxny": year,
        }
        _LOGGER.info("开始获取历史电费电量, 户号: [%s], 年份: [%s]", self._account_number, year)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        f"{BASE_APP_API_URL}/hlwyy/business-jffw/dldf/zztList",
                        timeout=MdejAPI.timeout,
                        params=params,
                        headers=self.get_header_with_token()
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"获取历史电费电量失败: HTTP 状态码 {response.status}, 响应: {text}")

                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)
                    if resp_json.get("code") != 0:
                        raise Exception(f"获取历史电费电量失败: code != 0, 响应: {resp_json}")

                    data = resp_json.get("data")
                    if not data:
                        raise Exception(f"获取历史电费电量失败: 未获取到数据, 响应: {resp_json}")

                    return data

            except Exception as e:
                _LOGGER.error("获取历史电费电量异常, 户号: [%s], 错误: [%s]", self._account_number, str(e))
                raise

    async def get_history_data(self):
        """组合当前周期前 12 个月历史数据与本期数据。"""
        now = datetime.datetime.now(tz)
        this_year = now.year
        this_month = now.month

        data_list = []
        last_year_data = await self.get_history(this_year - 1)

        for i in range(this_month, 13):
            month_str = "%d%02d" % (this_year - 1, i)
            data_list.append({
                ATTR_MONTH: month_str,
                ATTR_BILL: last_year_data["df"][i - 1],
                ATTR_CONSUMPTION: last_year_data["dl"][i - 1]
            })

        await asyncio.sleep(1)

        if this_month > 1:
            this_year_data = await self.get_history(this_year)
            for i in range(1, this_month):
                month_str = "%d%02d" % (this_year, i)
                data_list.append({
                    ATTR_MONTH: month_str,
                    ATTR_BILL: this_year_data["df"][i - 1],
                    ATTR_CONSUMPTION: this_year_data["dl"][i - 1]
                })
        else:
            this_year_data = None

        if this_month == 1:
            current = {
                ATTR_MONTH: ATTR_CURRENT,
                ATTR_BILL: last_year_data["bqdf"],
                ATTR_CONSUMPTION: last_year_data["bqdl"]
            }
        else:
            current = {
                ATTR_MONTH: ATTR_CURRENT,
                ATTR_BILL: this_year_data["bqdf"],
                ATTR_CONSUMPTION: this_year_data["bqdl"]
            }

        return {
            ATTR_HISTORY: data_list,
            ATTR_CURRENT: current
        }

    async def get_tiered_bill(self, year_month: str = None):
        """获取指定年月的阶梯电费信息。"""
        if not self._account_number:
            raise ValueError("必须先设置 account_number，才能获取阶梯电费")

        if year_month is None:
            today = datetime.datetime.now(tz)
            first_day_of_this_month = today.replace(day=1)
            previous_month_day = first_day_of_this_month - datetime.timedelta(days=1)
            year_month = previous_month_day.strftime("%Y%m")

        params = {
            "yhdabh": self._account_number,
            "fxny": year_month,
        }
        _LOGGER.info("开始获取阶梯电费, 户号: [%s], 年月: [%s]", self._account_number, year_month)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        f"{BASE_APP_API_URL}/hlwyy/business-mdej/jtyd/queryDfFxmxbList",
                        timeout=MdejAPI.timeout,
                        params=params,
                        headers=self.get_header_with_token()
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"获取阶梯电费失败: HTTP 状态码 {response.status}, 响应: {text}")

                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)
                    if resp_json.get("code") != 0:
                        raise Exception(f"获取阶梯电费失败: code != 0, 响应: {resp_json}")

                    data = resp_json.get("data") or {}
                    ydxx = data.get("ydxx") or []
                    if not ydxx:
                        raise Exception(f"获取阶梯电费失败: 未获取到阶梯明细, 响应: {resp_json}")

                    tiers = []
                    for item in ydxx:
                        tier = MdejAPI._safe_int(item.get("jtdw"), 0)
                        tiers.append({
                            ATTR_TIER: tier,
                            ATTR_TIER_NAME: MdejAPI.TIER_NAME_MAP.get(tier, f"第{tier}阶梯"),
                            ATTR_MONTH: item.get("month"),
                            ATTR_QUERY_MONTH: item.get("fxny") or year_month,
                            ATTR_CONSUMPTION: MdejAPI._safe_float(item.get("sdl")),
                            ATTR_PRICE: MdejAPI._safe_float(item.get("zhdj")),
                            ATTR_BILL: MdejAPI._safe_float(item.get("zdf")),
                        })

                    return {
                        ATTR_QUERY_MONTH: year_month,
                        ATTR_CURRENT_TIER: MdejAPI._safe_int(data.get("dqdw")),
                        ATTR_CURRENT_PRICE: MdejAPI._safe_float(data.get("dqdj")),
                        ATTR_TOTAL_CONSUMPTION: MdejAPI._safe_float(data.get("zsdl")),
                        ATTR_TOTAL_BILL: MdejAPI._safe_float(data.get("hjdf")),
                        ATTR_TIER_SPREAD_BILL: MdejAPI._safe_float(data.get("jtcedf")),
                        ATTR_PRICE_NAME: data.get("djmc"),
                        ATTR_PRICE_CODE: data.get("djdm"),
                        ATTR_TIERS: tiers,
                    }

            except Exception as e:
                _LOGGER.error("获取阶梯电费异常, 户号: [%s], 错误: [%s]", self._account_number, str(e))
                raise

    async def get_daily(self, days=30):
        """
        获取每日用电数据
        :return:
        """

        param = {
            "yhdabh": self._account_number,
            "ts": days
        }
        _LOGGER.info("开始获取每日用电数据, 户号: [%s]", self._account_number)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                        f"{BASE_APP_API_URL}/hlwyy/business-ggfw/khrydl/getKfrydl",
                        timeout=MdejAPI.timeout,
                        params=param,
                        headers=self.get_header_with_token()
                ) as response:
                    # 1. 检查 HTTP 状态码
                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("获取每日用电数据失败, 户号: [%s], 状态码: [%d], 响应: [%s]",
                                      self._account_number, response.status, text)
                        raise Exception(f"获取每日用电数据失败: HTTP 状态码 {response.status}, 响应: {text}")

                    # 2. 解析 JSON
                    resp_json = await response.json(encoding="utf-8")
                    MdejAPI._raise_if_auth_failed(resp_json)

                    # 3. 检查返回 code
                    if resp_json.get("code") != 0:
                        _LOGGER.error("获取每日用电数据失败, 户号: [%s], code != 0, 响应: [%s]",
                                      self._account_number, resp_json)
                        raise Exception(f"获取每日用电数据失败: code != 0, 响应: {resp_json}")

                    # 4. 获取 data
                    data_list = resp_json.get("data")
                    if not data_list:
                        _LOGGER.error("获取每日用电数据失败, 户号: [%s], 未获取到数据, 响应: [%s]",
                                      self._account_number, resp_json)
                        raise Exception(f"获取每日用电数据失败: 未获取到数据, 响应: {resp_json}")

                    _LOGGER.debug("开始处理每日用电数据")
                    transformed_data = []
                    for item in data_list:
                        # 原始日期字符串，例如 "2025/02/13"
                        rq = item.get("rq", "")
                        # 原始用电量字符串，例如 "18.25"
                        dl_str = item.get("dl", "0")

                        # 1. 解析日期，将 "YYYY/MM/DD" 转成 "YYYY-MM-DD"
                        try:
                            date_obj = datetime.datetime.strptime(rq, "%Y/%m/%d")
                            date_str = date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            # 如果日期格式有问题，可以根据实际情况做异常处理或默认值
                            date_str = rq  # 或者 continue、或 log 输出

                        # 2. 将用电量转换为浮点数
                        try:
                            consumption_val = float(dl_str)
                        except ValueError:
                            # 如果转换失败，也可以根据需要处理
                            consumption_val = 0.0

                        transformed_data.append({
                            ATTR_DATE: date_str,
                            ATTR_CONSUMPTION: consumption_val
                        })

                    _LOGGER.info("获取到每日用电数据, 户号: [%s], data: [%s]", self._account_number, transformed_data)
                    return transformed_data

            except Exception as e:
                _LOGGER.error("获取每日用电数据请求异常, 户号: [%s], 错误: [%s]",
                              self._account_number, str(e))
            raise
