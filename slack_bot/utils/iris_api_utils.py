# utils/iris_api_utils.py

import aiohttp
import asyncio

IRIS_API_URL = "https://api.domaintools.com/v1/iris-investigate/"

async def query_iris_api(api_key, api_user, search_hash):
    params = {
        'api_username': api_user,
        'api_key': api_key,
        'search_hash': search_hash
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(IRIS_API_URL, params=params) as response:
            if response.status != 200:
                raise Exception(f"Error querying Iris API: {response.status}")
            data = await response.json()
            return data
