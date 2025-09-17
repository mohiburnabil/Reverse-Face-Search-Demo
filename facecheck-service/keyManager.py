import asyncio
from typing import List
class KeyManager:
    def __init__(self, keys: List[str]):
        self.keys = keys
        self.available_keys = asyncio.Queue()
        for key in keys:
            self.available_keys.put_nowait(key)
    
    async def get_next_key(self):
        # Waits until a key is available
        key = await self.available_keys.get()
        return key
    
    async def release_key(self, key: str):
        # Returns the key back to the queue for reuse
        await self.available_keys.put(key)





