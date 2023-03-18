from typing import Any, Optional

from aiocache import SimpleMemoryCache


class CacheLimiter(SimpleMemoryCache):
    def __init__(self, ttl=60, max_value=10):
        super().__init__(ttl=ttl)
        self.max_value = max_value

    async def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if the user has exceeded the rate limit
        Returns True if rate limit is not exceeded, False otherwise
        """
        key = str(user_id)
        value = await self.get(key)
        if value is not None and value >= self.max_value:
            return False
        return True

    async def increment_rate_limit(self, user_id: int) -> None:
        """
        Increment the rate limit counter for the user
        """
        key = str(user_id)
        value = await self.get(key)
        if value is None:
            value = 1
        else:
            value += 1
        await self.set(key, value, ttl=self.ttl)

    async def clear_rate_limit(self, user_id: int) -> None:
        """
        Clear the rate limit counter for the user
        """
        key = str(user_id)
        await self.delete(key)
