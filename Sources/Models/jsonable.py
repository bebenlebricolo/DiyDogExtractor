from dataclasses import dataclass, field
from typing import Any, Optional, Generic, TypeVar, Union

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

    def read(self, content : dict) -> Any :
        return self.get_node(content)

    def try_read(self, content : dict, default : T) -> T:
        """Tries to access input dictionary content using self._prop_key and returns what's inside.
            if input node does not yield exploitable data, return the default value instead.
            End user knows what's inside this JsonProperty object and can use this knowledge to manipulate the data accordingly (
            this object has not enough knowledge to perform this kind of tasks alone (...))"""
        node = self.get_node(content)
        if node :
           return node
        return default

    def __eq__(self, other: object) -> bool:
        return self.value == other.value #type: ignore

@dataclass
class JsonOptionalProperty(JsonProperty[T]):
    # Masking JsonProperty value
    value : Optional[T] = None

    def __init__(self, key : str = "", val : Optional[T] = None) -> None:
        self._prop_key = key
        self.value = val
