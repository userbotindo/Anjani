from typing import TYPE_CHECKING, Any

from .anjani_mixin_base import MixinBase
from anjani import util

if TYPE_CHECKING:
    from .anjani_bot import Anjani


class DatabaseProvider(MixinBase):
    db: util.db.AsyncDatabase

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        client = util.db.AsyncClient(self.config["db_uri"], connect=False)
        self.db = client["AnjaniBot"]

        # Propagate initialization to other mixins
        super().__init__(**kwargs)
