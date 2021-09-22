from typing import TypeVar, Union

from pymongo import DeleteOne, InsertOne, ReplaceOne
from pymongo.read_preferences import (
    Primary,
    PrimaryPreferred,
    Secondary,
    SecondaryPreferred,
    Nearest
)

JavaScriptCode = TypeVar("JavaScriptCode", bound=str)
ReadPreferences = TypeVar(
    "ReadPreferences",
    bound=Union[
        Primary,
        PrimaryPreferred,
        Secondary,
        SecondaryPreferred,
        Nearest
    ]
)
Request = TypeVar("Request", bound=Union[DeleteOne, InsertOne, ReplaceOne])
Results = TypeVar("Results")
