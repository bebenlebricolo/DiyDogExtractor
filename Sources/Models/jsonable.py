from dataclasses import dataclass, field
from typing import Any, Optional, Generic, TypeVar

class Jsonable :
    def _read_prop(self, key : str, content : dict, default) :
        if key in content :
            return content[key]
        return default

    def to_json(self) -> dict :
        return {}

    def from_json(self, content : dict) -> None :
        pass

T = TypeVar("T")
@dataclass
class JsonProperty(Generic[T]):
    value : T
    _prop_key : str = field(default_factory=str)

    def __init__(self, key : str = "", val : T = None) -> None:
        self._prop_key = key
        self.value = val

    def get_node(self, content : dict) :
        if self._prop_key in content :
            return content[self._prop_key]
        return None

T = TypeVar("T")
@dataclass
class JsonOptionalProperty(Generic[T]):
    _prop_key : str = field(default_factory=str)
    value : Optional[T] = None

    def __init__(self, key : str = "", val : Optional[T] = None) -> None:
        self._prop_key = key
        self.value = val

    def get_node(self, content : dict) :
        if self._prop_key in content :
            return content[self._prop_key]
        return None