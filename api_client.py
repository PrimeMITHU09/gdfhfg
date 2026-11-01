import aiohttp
import asyncio
from typing import Dict, Any
from config import H143_API_KEY, H143_API_URL


async def fetch_proxy_stats(proxy_username: str) -> Dict[str, Any]:
    """
    Fetch real-time proxy stats from H143 API.
    Endpoint: https://h143.xyz/stats?api_key=...&username=...
    """
    url = H143_API_URL
    params = {
        "api_key": H143_API_KEY,
        "username": proxy_username.strip()
    }
    
    headers = {
        "User-Agent": "H143-Proxy-Checker-Bot/1.0"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return {
                        "success": False,
                        "error": f"HTTP Error {resp.status}",
                        "raw": await resp.text()
                    }
                
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    text_resp = await resp.text()
                    return {
                        "success": False,
                        "error": "Invalid JSON response",
                        "raw": text_resp
                    }

                # Check if API returned an error json (e.g. {"error": "not found"})
                if "error" in data:
                    return {
                        "success": False,
                        "error": data.get("error"),
                        "raw": data
                    }

                # Success case
                return {
                    "success": True,
                    "data": {
                        "mb_purchased": data.get("mb_purchased", 0),
                        "mb_remaining": data.get("mb_remaining", 0),
                        "mb_remaining_percentage": data.get("mb_remaining_percentage", 0),
                        "mb_used": data.get("mb_used", 0),
                        "mb_used_percentage": data.get("mb_used_percentage", 0),
                        "username": data.get("username", proxy_username)
                    }
                }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Request timed out. Please try again."
        }
    except aiohttp.ClientConnectorError:
        return {
            "success": False,
            "error": "Unable to connect to H143 server. Please check your internet connection."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

