from typing import TYPE_CHECKING, Any

Base: Any
if TYPE_CHECKING:
    from .anjani import Anjani

    Base = Anjani
else:
    import abc

    Base = abc.ABC