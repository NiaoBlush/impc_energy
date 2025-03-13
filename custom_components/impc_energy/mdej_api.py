# 蒙电e家api
import datetime
import aiohttp
import logging

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64
import json

from .const import (
    BASE_APP_API_URL
)

_LOGGER = logging.getLogger(__name__)
tz = datetime.timezone(datetime.timedelta(hours=+8))


class MdejAPI(object):
    def __init__(self, session: aiohttp.ClientSession, username, payload):
        self.session = session
        self._username = username
        self._payload = payload
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

    @staticmethod
    def get_public_key():
        return """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCa4++f6RUofKGRZjbTDd3fOah6CyDb+PB8Spsp/2t1MCzHX5vJoD9E9L5U6lGOORNER4xvjRm3eTGUDEYYZS3FZqkwvIlp7EyFiAa5VNzZ+rhcZiwBJUavL6RmRVwX06s7O8IpeGprm1vz9+OTjDA1tKq0VE8dy33ziglW3ArI9wIDAQAB
-----END PUBLIC KEY-----
"""

    @staticmethod
    def cal_payload(username, pwd):
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

        pub_key = RSA.importKey(MdejAPI.get_public_key())
        cipher = PKCS1_v1_5.new(pub_key)

        encrypted_bytes = cipher.encrypt(plaintext)
        encrypted_base64_str = base64.b64encode(encrypted_bytes).decode('utf-8')
        _LOGGER.debug("得到登录payload: %s...", encrypted_base64_str[:10])

        return encrypted_base64_str

    async def get_token(self, payload):
        """
        登录以获取token
        :return:
        """

        data = {
            "payLoad": payload,
            "publicKey": MdejAPI.get_public_key()
        }
        _LOGGER.debug("开始登录app, 用户: [%s]", self._username)
        try:
            async with self.session.post(
                    f"{BASE_APP_API_URL}/hlwyy/business-zhfw/account/loginNew3",
                    timeout=MdejAPI.timeout,
                    json=data,  # 使用 `json=` 传递数据
                    headers=MdejAPI.header
            ) as response:

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("登录失败, 用户: [%s], 状态码: [%d], 响应: [%s]", self._username, response.status, text)
                    return None

                resp_json = await response.json(encoding="utf-8")
                token = resp_json.get("data", {}).get("token")

                if not token:
                    _LOGGER.error("登录失败, 用户: [%s], 未获取到 token, 响应: [%s]", self._username, resp_json)
                    return None

                _LOGGER.info("登录成功, 用户: [%s]", self._username)
                self._token = token
                return token

        except Exception as e:
            _LOGGER.error("登录请求异常, 用户: [%s], 错误: [%s]", self._username, str(e))
            return None
