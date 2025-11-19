"""A.O. Smith API client with command sending support."""
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
    
    BASE_URL = "https://ailink-api.hotwater.com.cn/AiLinkService"
    
    def __init__(self, access_token: str, user_id: str, family_id: str, cookie: str = None, mobile: str = None):
        self._access_token = access_token
        self._user_id = user_id
        self._family_id = family_id
        self._cookie = cookie
        self._mobile = mobile
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def async_authenticate(self):
        """Create aiohttp session."""
        self._session = aiohttp.ClientSession()
    
    async def async_get_devices(self) -> List[Dict[str, Any]]:
        """Get list of user devices."""
        payload = {"encode": self._generate_encode(self._user_id), "homePageVersion": "3",
                   "userId": self._user_id, "familyId": self._family_id}
        headers = await self._generate_headers(payload)
        devices = []
        try:
            async with self._session.post(f"{self.BASE_URL}/appDevice/getHomepageV2",
                                          json=payload, headers=headers) as resp:
                text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error("HTTP error %s: %s", resp.status, text)
                    return []
                data = await resp.json()
                if data.get("status") != 200:
                    _LOGGER.error("API error: %s", data.get("msg"))
                    return []
                info = data.get("info", {})
                # 优先 devInfoItemInfoList
                devices = info.get("devInfoItemInfoList", [])
                if not devices:
                    for room in info.get("roomInfoItemInfoList", []):
                        devices.extend(room.get("deviceList", []))
                return devices
        except Exception as e:
            _LOGGER.exception("Failed to get devices: %s", e)
            return []
    
    async def async_get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current device status."""
        payload = {"userId": self._user_id, "familyId": self._family_id,
                   "deviceId": device_id, "encode": self._generate_encode(device_id)}
        headers = await self._generate_headers(payload)
        try:
            async with self._session.post(f"{self.BASE_URL}/appDevice/getDeviceCurrInfo",
                                          json=payload, headers=headers) as resp:
                text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error("HTTP error %s: %s", resp.status, text)
                    return None
                data = await resp.json()
                if data.get("status") != 200:
                    _LOGGER.error("API error: %s", data.get("msg"))
                    return None
                return data.get("info", {})
        except Exception as e:
            _LOGGER.exception("Failed to get device status for %s: %s", device_id, e)
            return None
    
    async def async_send_command(self, device_id: str, service_identifier: str, input_data: Dict[str, Any]):
        """Send control command to device (temperature, mode, zero cold water)."""
        payload = {
            "userId": self._user_id,
            "familyId": self._family_id,
            "appSource": 2,
            "commandSource": 1,
            "invokeTime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "payLoad": json.dumps({
                "profile": {
                    "deviceId": device_id,
                    "productType": "19",
                    "deviceType": "JSQ31-VJS"
                },
                "service": {
                    "identifier": service_identifier,
                    "inputData": input_data
                }
            }, ensure_ascii=False)
        }
        headers = await self._generate_headers(payload)
        try:
            async with self._session.post(f"{self.BASE_URL}/device/invokeMethod",
                                          json=payload, headers=headers) as resp:
                text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error("Command HTTP error %s: %s", resp.status, text)
                    return None
                data = await resp.json()
                _LOGGER.debug("Command response: %s", json.dumps(data, ensure_ascii=False))
                return data
        except Exception as e:
            _LOGGER.exception("Failed to send command to %s: %s", device_id, e)
            return None
    
    async def _generate_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4()).upper()
        return {
            "Host": "ailink-api.hotwater.com.cn",
            "Authorization": f"Bearer {self._access_token}",
            "version": "V1.0.1",
            "familyUk": "",
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
    
    def _generate_md5data(self, payload: Dict[str, Any]) -> str:
        try:
            json_str = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            return hashlib.md5(json_str.encode('utf-8')).hexdigest()
        except Exception:
            return ""
    
    def _generate_encode(self, input_str: str) -> str:
        timestamp = str(int(time.time()))
        return hashlib.md5(f"{input_str}{timestamp}".encode()).hexdigest()
    
    async def close(self):
        if self._session:
            await self._session.close()
