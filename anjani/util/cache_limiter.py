from aiocache.backends.memory import SimpleMemoryCache


class CacheLimiter(SimpleMemoryCache):
    # Initialized during instantiation
    max_value: int

    def __init__(self, ttl: int = 60, max_value: int = 10) -> None:
        super().__init__(ttl=ttl)

        self.max_value = max_value

    async def increment(self, user_id: int) -> None:  # skipcq: PYL-W0221
        """
        Increment the rate limit of the user
        """
        val = await self.get(user_id)
        await self.set(user_id, 1 if not val else val + 1, ttl=self.ttl)

    async def exceeded(self, user_id: int) -> bool:
        """
        Check if the user has exceeded the rate limit
        """
        val = await self.get(user_id)
        if not val:
            return False

        return val >= self.max_value
