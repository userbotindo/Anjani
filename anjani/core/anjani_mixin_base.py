from typing import TYPE_CHECKING, Any

MixinBase: Any
if TYPE_CHECKING:
    from .anjani_bot import Anjani

    MixinBase = Anjani
else:
    import abc

    MixinBase = abc.ABC