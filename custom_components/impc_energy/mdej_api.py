# 蒙电e家api

import datetime
import aiohttp
import asyncio
import logging

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64
import json

from .const import (
    BASE_APP_API_URL,
    ATTR_DATE,
    ATTR_CONSUMPTION
)

_LOGGER = logging.getLogger(__name__)
tz = datetime.timezone(datetime.timedelta(hours=+8))


class MdejAPI(object):
    def __init__(self, username):
        self._username = username
        self._account_number = None
        self._account_name = None
        self._public_key = None
        self._login_payload = None
        self._token = None

    timeout = aiohttp.ClientTimeout(total=60)
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

    def account_number(self) -> str:
        return self._account_number

    def set_account_number(self, account_number):
        """
        设置户号
        部分接口需要户号参数
        """
        self._account_number = account_number

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

    async def initialize(self, username=None, pwd=None, login_payload=None, token=None):
        """
        初始化 需要手动调用
        获取公钥, 登录

        使用login_payload初始化时必报错, 原因未知
        :return:
        """
        await self._get_public_key()
        if token:
            _LOGGER.debug("使用token初始化")
            self._token = token
        else:
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
            "version": "3.0.3"
        }
        plaintext = json.dumps(data_to_encrypt).encode('utf-8')

        pub_key_str = self._get_pub_key_pem()
        pub_key = RSA.importKey(pub_key_str)
        cipher = PKCS1_v1_5.new(pub_key)

        encrypted_bytes = cipher.encrypt(plaintext)
        encrypted_base64_str = base64.b64encode(encrypted_bytes).decode('utf-8')
        _LOGGER.debug("得到登录payload: [%s...]", encrypted_base64_str[:10])

        return encrypted_base64_str

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
