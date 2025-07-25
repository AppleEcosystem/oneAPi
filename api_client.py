import aiohttp
from typing import Optional, Dict, Any, List

class OneBotAPIClient:
    """Client for OneBot API"""
    
    def __init__(self, base_url: str = "https://api.bot1.org"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, api_key: str, 
                          data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/x-www-form-urlencoded" if data else "application/json"
        }
        
        # Use a new session for each request to avoid unclosed session issues
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, headers=headers, data=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(f"API request failed: {response.status}")
            except aiohttp.ClientError as e:
                raise Exception(f"Network error: {e}")
    
    async def get_balance(self, api_key: str) -> float:
        """Get account balance"""
        result = await self._make_request("GET", "/balance", api_key)
        return float(result)
    
    async def register_udid(self, api_key: str, udid: str, plan: str) -> Dict[str, Any]:
        """Register UDID with selected plan"""
        data = {
            "udid": udid,
            "register_plan": plan
        }
        return await self._make_request("POST", "/register", api_key, data)
    
    async def get_certificate(self, api_key: str, udid: str = None, 
                            certificate_id: str = None) -> List[Dict[str, Any]]:
        """Get certificate information"""
        params = []
        if udid:
            params.append(f"udid={udid}")
        if certificate_id:
            params.append(f"certificate_id={certificate_id}")
        
        endpoint = "/certificate"
        if params:
            endpoint += "?" + "&".join(params)
        
        result = await self._make_request("GET", endpoint, api_key)
        return result if isinstance(result, list) else [result]
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
