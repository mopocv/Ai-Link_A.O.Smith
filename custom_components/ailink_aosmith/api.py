"""A.O. Smith API client."""
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
        """Initialize the API client."""
        self._access_token = access_token
        self._user_id = user_id
        self._family_id = family_id
        self._cookie = cookie
        self._mobile = mobile
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def async_authenticate(self):
        """Create session."""
        self._session = aiohttp.ClientSession()
        
    async def async_get_devices(self) -> List[Dict[str, Any]]:
        """Get list of user devices using getHomepageV2 endpoint."""
        encode = self._generate_encode(self._user_id)
        
        payload = {
            "encode": encode,
            "homePageVersion": "3", 
            "userId": self._user_id,
            "familyId": self._family_id
        }
        
        headers = await self._generate_headers(payload)
        
        try:
            async with self._session.post(
                "https://ailink-api.hotwater.com.cn/AiLinkService/appDevice/getHomepageV2",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Device list response: %s", json.dumps(data, indent=2))
                    
                    if data.get("status") == 200:
                        info = data.get("info", {})
                        devices = []
                        
                        # Extract from deviceList
                        if "deviceList" in info:
                            devices.extend(info["deviceList"])
                        
                        # Extract from spaceDeviceMapping  
                        if "spaceDeviceMapping" in info:
                            for space_device in info["spaceDeviceMapping"]:
                                if "appDeviceEntityList" in space_device:
                                    devices.extend(space_device["appDeviceEntityList"])
                        
                        # Filter for water heater devices
                        water_heaters = [
                            device for device in devices 
                            if device.get("productMajorClassCode") == "19"
                        ]
                        
                        _LOGGER.info("Found %d water heater devices", len(water_heaters))
                        for device in water_heaters:
                            _LOGGER.info("Device: %s (ID: %s, Model: %s)", 
                                       device.get("deviceName"), 
                                       device.get("deviceId"),
                                       device.get("productModel"))
                        
                        return water_heaters
                    else:
                        _LOGGER.error("API error: %s", data.get("msg"))
                else:
                    _LOGGER.error("HTTP error: %s", response.status)
        except Exception as e:
            _LOGGER.error("Failed to get devices: %s", e)
            
        return []
    
    async def async_get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current device status."""
        encode = self._generate_encode(device_id)
        
        payload = {
            "userId": self._user_id,
            "familyId": self._family_id,
            "deviceId": device_id,
            "encode": encode
        }
        
        headers = await self._generate_headers(payload)
        
        try:
            async with self._session.post(
                "https://ailink-api.hotwater.com.cn/AiLinkService/appDevice/getDeviceCurrInfo",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Device status response for %s: %s", device_id, json.dumps(data, indent=2))
                    
                    if data.get("status") == 200:
                        return data.get("info")
                    else:
                        _LOGGER.error("API error for device %s: %s", device_id, data.get("msg"))
                else:
                    _LOGGER.error("HTTP error for device %s: %s", device_id, response.status)
        except Exception as e:
            _LOGGER.error("Failed to get device status for %s: %s", device_id, e)
            
        return None
    
    async def async_get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        if not self._mobile:
            _LOGGER.warning("Mobile number not provided, skipping account info")
            return None
            
        encode = self._generate_encode(self._mobile)
        
        payload = {
            "encode": encode,
            "mobile": self._mobile,
            "userId": self._user_id
        }
        
        headers = await self._generate_headers(payload)
        
        try:
            async with self._session.post(
                "https://ailink-api.hotwater.com.cn/AiLinkService/lock/getAccountInfo",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 200:
                        return data.get("info")
                    else:
                        _LOGGER.error("Account info API error: %s", data.get("msg"))
                else:
                    _LOGGER.error("Account info HTTP error: %s", response.status)
        except Exception as e:
            _LOGGER.error("Failed to get account info: %s", e)
            
        return None
    
    async def _generate_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Generate request headers."""
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4()).upper()
        
        headers = {
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
            "Cookie": self._cookie,
            "sign": "",  # 留空
        }
        
        return headers
    
    def _generate_md5data(self, payload: Dict[str, Any]) -> str:
        """Generate md5data by hashing the JSON payload."""
        try:
            json_str = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            _LOGGER.debug("JSON string for MD5: %s", json_str)
            
            md5_hash = hashlib.md5(json_str.encode('utf-8')).hexdigest()
            _LOGGER.debug("Generated MD5: %s", md5_hash)
            
            return md5_hash
        except Exception as e:
            _LOGGER.error("Failed to generate md5data: %s", e)
            return "7502271d2d3217c6aa2d80e21ebeed51"
    
    def _generate_encode(self, input_str: str) -> str:
        """Generate encode parameter."""
        timestamp = str(int(time.time()))
        input_data = f"{input_str}{timestamp}"
        return hashlib.md5(input_data.encode()).hexdigest()
    
    @property
    def is_authenticated(self) -> bool:
        """Return if authenticated."""
        return self._access_token is not None and self._user_id is not None
    
    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()