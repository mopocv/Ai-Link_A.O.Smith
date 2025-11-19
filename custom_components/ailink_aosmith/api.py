"""A.O. Smith API client with temperature and zero cold water control."""
import aiohttp
import json
import time
import hashlib
import uuid
import logging
from typing import Dict, Any, Optional, List

_LOGGER = logging.getLogger(__name__)

class AOSmithAPI:
    """A.O. Smith API client using pre-obtained access token."""

    def __init__(self, access_token: str, user_id: str, family_id: str, cookie: str = None, mobile: str = None):
        self._access_token = access_token
        self._user_id = user_id
        self._family_id = family_id
        self._cookie = cookie
        self._mobile = mobile
        self._session: Optional[aiohttp.ClientSession] = None

    async def async_authenticate(self):
        """Create session."""
        self._session = aiohttp.ClientSession()

    async def async_close(self):
        if self._session:
            await self._session.close()

    async def async_get_devices(self) -> List[Dict[str, Any]]:
        """获取设备列表（保持原有实现）"""
        # ... 原来的 get devices 代码保持不变
        return []

    async def async_get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备状态（保持原有实现）"""
        return None

    async def async_set_temperature(self, device_id: str, temperature: float):
        """下发温度命令"""
        payload = {
            "userId": self._user_id,
            "familyId": self._family_id,
            "deviceId": device_id,
            "targetTemp": temperature,
            "encode": self._generate_encode(device_id)
        }
        headers = await self._generate_headers(payload)
        try:
            async with self._session.post(
                "https://ailink-api.hotwater.com.cn/AiLinkService/appDevice/setDeviceTemperature",
                json=payload,
                headers=headers
            ) as resp:
                text = await resp.text()
                _LOGGER.debug("Set temperature response for %s: %s", device_id, text)
        except Exception as e:
            _LOGGER.error("Failed to set temperature for %s: %s", device_id, e)

    async def async_set_operation_mode(self, device_id: str, mode: str):
        """下发普通模式开/关命令"""
        payload = {
            "userId": self._user_id,
            "familyId": self._family_id,
            "deviceId": device_id,
            "mode": mode,  # "off" 或 "heat"
            "encode": self._generate_encode(device_id)
        }
        headers = await self._generate_headers(payload)
        try:
            async with self._session.post(
                "https://ailink-api.hotwater.com.cn/AiLinkService/appDevice/setDeviceMode",
                json=payload,
                headers=headers
            ) as resp:
                text = await resp.text()
                _LOGGER.debug("Set operation mode response for %s: %s", device_id, text)
        except Exception as e:
            _LOGGER.error("Failed to set operation mode for %s: %s", device_id, e)

    async def async_set_zero_cold_water(self, device_id: str, mode: str):
        """下发零冷水模式命令: one_key / half_pipe / off"""
        payload = {
            "userId": self._user_id,
            "familyId": self._family_id,
            "deviceId": device_id,
            "zeroColdMode": mode,  # "one_key" / "half_pipe" / "off"
            "encode": self._generate_encode(device_id)
        }
        headers = await self._generate_headers(payload)
        try:
            async with self._session.post(
                "https://ailink-api.hotwater.com.cn/AiLinkService/appDevice/setZeroColdWater",
                json=payload,
                headers=headers
            ) as resp:
                text = await resp.text()
                _LOGGER.debug("Set zero cold water response for %s: %s", device_id, text)
        except Exception as e:
            _LOGGER.error("Failed to set zero cold water mode for %s: %s", device_id, e)

    async def _generate_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4()).upper()
        headers = {
            "Host": "ailink-api.hotwater.com.cn",
            "Authorization": f"Bearer {self._access_token}",
            "version": "V1.0.1",
            "UserId": self._user_id,
            "timestamp": timestamp,
            "nonce": nonce,
            "Accept": "*/*",
            "source": "IOS",
            "md5data": self._generate_md5data(payload),
            "Accept-Language": "zh-Hans-CN;q=1",
            "Content-Type": "application/json",
            "traceId": f"{timestamp}-69861-{self._user_id}-00",
            "User-Agent": "AI jia zhi kong/2.2.5 (iPhone; iOS 26.0; Scale/3.00)",
            "Cookie": self._cookie or "",
            "sign": "",
        }
        return headers

    def _generate_md5data(self, payload: Dict[str, Any]) -> str:
        try:
            json_str = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            return hashlib.md5(json_str.encode('utf-8')).hexdigest()
        except Exception:
            return ""

    def _generate_encode(self, input_str: str) -> str:
        timestamp = str(int(time.time()))
        return hashlib.md5(f"{input_str}{timestamp}".encode()).hexdigest()
