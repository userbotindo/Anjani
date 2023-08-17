from abc import abstractmethod, abstractproperty
from typing import Any, Callable, Protocol

from aiohttp import ClientSession

from .common import DecoratedCallable, Instantiable, TypeData


class NDArray(Protocol[TypeData]):
    @abstractmethod
    def __getitem__(self, key: int) -> Any:
        raise NotImplementedError

    @abstractproperty
    def size(self) -> int:
        raise NotImplementedError


class Classifier(Protocol):
    @abstractmethod
    async def predict(self, text: str, **predict_params: Any) -> NDArray[Any]:
        raise NotImplementedError

    @abstractmethod
    async def load_model(self, http_client: ClientSession) -> None:
        raise NotImplementedError

    @abstractmethod
    async def is_spam(self, text: str) -> bool:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def normalize(text: str) -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def prob_to_string(value: float) -> str:
        raise NotImplementedError


class WebServer(Protocol):
    @abstractmethod
    async def run(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_router(self, **router_param: Any) -> None:
        raise NotImplementedError


class Router(Instantiable):
    def get(self, *args, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
        raise NotImplementedError

    def post(self, *args, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
        raise NotImplementedError

    def put(self, *args, **kwargs) -> Callable[[DecoratedCallable], DecoratedCallable]:
        raise NotImplementedError
