import aiohttp
from typing import Optional

class URLShortener:
    """URL shortening service using dropl.link"""
    
    def __init__(self):
        self.api_url = "https://www.dropl.link/api/shorten"
    
    async def shorten_url(self, long_url: str, expiration_days: int = 1) -> Optional[str]:
        """Shorten a URL using dropl.link API"""
        try:
            payload = {
                "url": long_url,
                "expirationDays": expiration_days
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Use context manager to ensure session is properly closed
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        short_url = result.get('shortUrl')
                        if short_url:
                            return short_url
                        else:
                            return long_url
                    else:
                        return long_url
                        
        except Exception as e:
            return long_url
    
    async def shorten_install_url(self, install_url: str) -> str:
        """Shorten install URL with 1 day expiration"""
        return await self.shorten_url(install_url, expiration_days=1)
