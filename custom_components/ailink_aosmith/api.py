"""A.O. Smith API client."""
import aiohttp
import json
import time
import hashlib
import uuid
import logging
from typing import Dict, Any, Optional, List
from .const import API_BASE_URL, DEVICE_CATEGORY_WATER_HEATER

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
        self._is_authenticated = False
        
    async def async_authenticate(self):
        """Create session and verify authentication."""
        if self._session:
            await self.close()
            
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        
        try:
            # Test authentication by trying to get devices
            devices = await self.async_get_devices()
            if devices:
                self._is_authenticated = True
                _LOGGER.info("Authentication successful, found %d devices", len(devices))
            else:
                raise Exception("No devices found - authentication may have failed")
        except Exception as e:
            await self.close()
            raise Exception(f"Authentication failed: {e}")
    
    async def async_get_devices(self) -> List[Dict[str, Any]]:
        """Get list of user devices using getHomepageV2 endpoint."""
        if not self._session:
            raise Exception("API not authenticated")
            
        encode = self._generate_encode(self._user_id)
        
        payload = {
            "encode": encode,
            "homePageVersion": "3", 
            "userId": self._user_id,
            "familyId": self._family_id
        }
        
        headers = await self._generate_headers(payload)
        
        _LOGGER.debug("Getting devices with payload: %s", payload)
        
        try:
            async with self._session.post(
                f"{API_BASE_URL}/AiLinkService/appDevice/getHomepageV2",
                json=payload,
                headers=headers
            ) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        _LOGGER.debug("Device list response status: %s", data.get("status"))
                        
                        if data.get("status") == 200:
                            info = data.get("info", {})
                            
                            # Extract devices from multiple possible locations
                            devices = []
                            
                            # From devInfoItemInfoList
                            if "devInfoItemInfoList" in info:
                                devices.extend(info["devInfoItemInfoList"])
                                _LOGGER.debug("Found %d devices in devInfoItemInfoList", len(info["devInfoItemInfoList"]))
                            
                            # From roomInfoItemInfoList
                            if not devices and "roomInfoItemInfoList" in info:
                                for room_info in info["roomInfoItemInfoList"]:
                                    if "deviceList" in room_info:
                                        devices.extend(room_info["deviceList"])
                                        _LOGGER.debug("Found %d devices in room %s", 
                                                    len(room_info["deviceList"]), room_info.get("roomName"))
                            
                            # Filter water heater devices
                            water_heaters = [
                                device for device in devices 
                                if str(device.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER
                            ]
                            
                            _LOGGER.info("Found %d water heater devices", len(water_heaters))
                            for device in water_heaters:
                                _LOGGER.info("Device: %s (ID: %s, Category: %s, Model: %s)", 
                                           device.get("productName"), 
                                           device.get("deviceId"),
                                           device.get("deviceCategory"),
                                           device.get("productModel"))
                            
                            return water_heaters
                        else:
                            error_msg = f"API returned error status: {data.get('status')}, message: {data.get('msg')}"
                            _LOGGER.error(error_msg)
                            raise Exception(error_msg)
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse JSON response: {e}, raw response: {response_text[:200]}"
                        _LOGGER.error(error_msg)
                        raise Exception(error_msg)
                else:
                    error_msg = f"HTTP error {response.status}: {response_text[:200]}"
                    _LOGGER.error(error_msg)
                    raise Exception(error_msg)
                    
        except asyncio.TimeoutError:
            error_msg = "Timeout while getting devices"
            _LOGGER.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to get devices: {e}"
            _LOGGER.error(error_msg)
            raise Exception(error_msg)
            
    async def async_get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current device status."""
        if not self._session:
            raise Exception("API not authenticated")
            
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
                f"{API_BASE_URL}/AiLinkService/appDevice/getDeviceCurrInfo",
                json=payload,
                headers=headers
            ) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        
                        if data.get("status") == 200:
                            info = data.get("info", {})
                            _LOGGER.debug("Device status info for %s - productModel: %s", 
                                        device_id, info.get("productModel"))
                            return info
                        else:
                            _LOGGER.warning("API error for device %s: %s", device_id, data.get("msg"))
                            return None
                    except json.JSONDecodeError as e:
                        _LOGGER.warning("Failed to parse device status JSON for %s: %s", device_id, e)
                        return None
                else:
                    _LOGGER.warning("HTTP error for device %s: %s", device_id, response.status)
                    return None
                    
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout getting device status for %s", device_id)
            return None
        except Exception as e:
            _LOGGER.warning("Failed to get device status for %s: %s", device_id, e)
            return None
    
    async def async_send_command(self, device_id: str, service_identifier: str, input_data: Dict[str, Any] = None):
        """Send control command to device."""
        if not self._session:
            raise Exception("API not authenticated")
            
        if input_data is None:
            input_data = {}

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
            async with self._session.post(
                f"{API_BASE_URL}/AiLinkService/device/invokeMethod",
                json=payload, 
                headers=headers
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error("Command HTTP error %s: %s", resp.status, text)
                    return None
                data = await resp.json()
                _LOGGER.debug("Command response: %s", json.dumps(data, ensure_ascii=False))
                return data
        except Exception as e:
            _LOGGER.error("Failed to send command to %s: %s", device_id, e)
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
            "Cookie": self._cookie or "",
            "sign": "",
        }
        
        return headers
    
    def _generate_md5data(self, payload: Dict[str, Any]) -> str:
        """Generate md5data by hashing the JSON payload."""
        try:
            json_str = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            md5_hash = hashlib.md5(json_str.encode('utf-8')).hexdigest()
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
        return self._is_authenticated
    
    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None
            self._is_authenticated = False