from typing import TYPE_CHECKING, Any

from motor.core import AgnosticCollection
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .anjani_mixin_base import MixinBase
from anjani import util

if TYPE_CHECKING:
    from .anjani_bot import Anjani


class DataBase(MixinBase):
    db: AsyncIOMotorDatabase
    _db: AsyncIOMotorClient

    def __init__(self: "Anjani", **kwargs: Any):
        self._init_db()

        self.db = self._db.get_database("AnjaniBot")

        super().__init__(**kwargs)

    def _init_db(self: "Anjani") -> None:
        self._db = AsyncIOMotorClient(self.config["db_uri"], connect=False)

    def get_collection(self: "Anjani", name: str) -> AgnosticCollection:
        return self.db.get_collection(name)

    async def close_db(self: "Anjani") -> None:
        await util.run_sync(self._db.close)