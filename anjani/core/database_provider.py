from typing import TYPE_CHECKING, Any

from .anjani_mixin_base import MixinBase
from anjani import util

from pymongo.driver_info import DriverInfo

if TYPE_CHECKING:
    from .anjani_bot import Anjani


class DatabaseProvider(MixinBase):
    db: util.db.AsyncDB

    def __init__(self: "Anjani", **kwargs: Any):
        driver = DriverInfo("AsyncIOMongoDB", "alpha", "AsyncIO")
        client = util.db.AsyncClient(self.config["db_uri"],
                                     connect=False,
                                     driver=driver)
        self.db = client["AnjaniBot"]

        # Propagate initialization to other mixins
        super().__init__(**kwargs)
